type BadgeVariant = "default" | "success" | "warning" | "danger" | "info" |
                   "business" | "analytics" | "knowledge" | "vision";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: "sm" | "md";
  className?: string;
}

const variants: Record<BadgeVariant, string> = {
  default:   "bg-slate-700 text-slate-300",
  success:   "bg-green-500/20 text-green-400 border border-green-500/30",
  warning:   "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
  danger:    "bg-red-500/20 text-red-400 border border-red-500/30",
  info:      "bg-blue-500/20 text-blue-400 border border-blue-500/30",
  // AI intent action types
  business:  "bg-orange-500/20 text-orange-400 border border-orange-500/30",
  analytics: "bg-blue-500/20 text-blue-300 border border-blue-500/30",
  knowledge: "bg-teal-500/20 text-teal-400 border border-teal-500/30",
  vision:    "bg-purple-500/20 text-purple-400 border border-purple-500/30",
};

export default function Badge({ children, variant = "default", size = "sm", className = "" }: BadgeProps) {
  return (
    <span className={`inline-flex items-center font-medium rounded-full
                      ${size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm"}
                      ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
}
