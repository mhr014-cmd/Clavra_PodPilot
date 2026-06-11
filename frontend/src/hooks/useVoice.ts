/**
 * Voice hook — Clavra ProdPilot™
 *
 * STT:  Web Speech API (SpeechRecognition) — free, browser-native, no API key.
 *       Falls back to silent no-op on unsupported browsers.
 * TTS:  Web Speech Synthesis — free, browser-native.
 *       Falls back to server-side OpenAI TTS if Web Synthesis isn't available.
 */
import { useState, useRef, useCallback, useEffect } from "react";
import api from "../api/axios";

// Extend window types for webkit prefix
declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition;
    webkitSpeechRecognition: typeof SpeechRecognition;
  }
}

function getSpeechRecognition(): SpeechRecognition | null {
  const Ctor = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Ctor) return null;
  const r = new Ctor();
  r.continuous      = false;
  r.interimResults  = true;
  r.lang            = "en-US";
  r.maxAlternatives = 1;
  return r;
}

export function useVoice() {
  const [isRecording, setIsRecording] = useState(false);
  const [isPlaying, setIsPlaying]     = useState(false);
  const [transcript, setTranscript]   = useState("");

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const synthRef       = useRef<SpeechSynthesisUtterance | null>(null);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      recognitionRef.current?.abort();
      window.speechSynthesis?.cancel();
    };
  }, []);

  // ── Speech Recognition (STT) ──────────────────────────────────────────

  const startRecording = useCallback(() => {
    const rec = getSpeechRecognition();
    if (!rec) {
      console.warn("SpeechRecognition not supported in this browser.");
      return;
    }

    let finalTranscript = "";

    rec.onstart  = () => setIsRecording(true);
    rec.onend    = () => {
      setIsRecording(false);
      if (finalTranscript) setTranscript(finalTranscript);
    };
    rec.onerror  = () => setIsRecording(false);

    rec.onresult = (e: SpeechRecognitionEvent) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) finalTranscript += t;
        else interim += t;
      }
      // Show interim result while speaking
      setTranscript(finalTranscript + interim);
    };

    recognitionRef.current = rec;
    rec.start();
  }, []);

  const stopRecording = useCallback(() => {
    recognitionRef.current?.stop();
    setIsRecording(false);
  }, []);

  const toggleRecording = useCallback(() => {
    if (isRecording) stopRecording();
    else startRecording();
  }, [isRecording, startRecording, stopRecording]);

  // ── Text-to-Speech (TTS) ──────────────────────────────────────────────

  const playText = useCallback(async (text: string) => {
    if (!text.trim()) return;

    // Prefer browser synthesis (free, no API key)
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const utt  = new SpeechSynthesisUtterance(text);
      utt.lang   = "en-US";
      utt.rate   = 1.0;
      utt.pitch  = 1.0;

      // Pick a natural English voice if available
      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(
        (v) => v.lang.startsWith("en") && (v.name.includes("Google") || v.name.includes("Natural") || v.name.includes("Premium"))
      ) ?? voices.find((v) => v.lang.startsWith("en"));
      if (preferred) utt.voice = preferred;

      utt.onstart = () => setIsPlaying(true);
      utt.onend   = () => setIsPlaying(false);
      utt.onerror = () => setIsPlaying(false);

      synthRef.current = utt;
      window.speechSynthesis.speak(utt);
      return;
    }

    // Fallback: server-side OpenAI TTS (only works with API credits)
    try {
      setIsPlaying(true);
      const res = await api.post("/ai/voice/speak", { text }, { responseType: "blob" });
      if (res.data?.size > 0) {
        const url   = URL.createObjectURL(res.data);
        const audio = new Audio(url);
        audio.onended = () => { setIsPlaying(false); URL.revokeObjectURL(url); };
        audio.play();
      } else {
        setIsPlaying(false);
      }
    } catch {
      setIsPlaying(false);
    }
  }, []);

  const stopPlaying = useCallback(() => {
    window.speechSynthesis?.cancel();
    setIsPlaying(false);
  }, []);

  const clearTranscript = useCallback(() => setTranscript(""), []);

  return {
    isRecording,
    isPlaying,
    transcript,
    clearTranscript,
    toggleRecording,
    startRecording,
    stopRecording,
    playText,
    stopPlaying,
  };
}
