import { useRef } from "react";
interface Props { onImageSelect: (file: File) => void; }
export default function ImageUploadZone({ onImageSelect }: Props) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <>
      <input ref={ref} type="file" accept="image/*" className="hidden"
        onChange={e => { if (e.target.files?.[0]) onImageSelect(e.target.files[0]); e.target.value = ""; }}
      />
      <button onClick={() => ref.current?.click()}
        className="flex-shrink-0 w-12 h-12 rounded-xl bg-slate-700 hover:bg-slate-600
                   flex items-center justify-center transition"
        title="Upload image for vision analysis"
      >
        <svg className="w-5 h-5 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </button>
    </>
  );
}
