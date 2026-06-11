interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: "sm" | "md" | "lg" | "none";
  hover?: boolean;
}

const paddings = { none: "", sm: "p-4", md: "p-6", lg: "p-8" };

export default function Card({ children, className = "", padding = "md", hover = false }: CardProps) {
  return (
    <div className={`bg-slate-800/60 backdrop-blur-sm border border-slate-700/50 rounded-2xl
                     ${paddings[padding]}
                     ${hover ? "hover:border-slate-600 hover:bg-slate-800 transition-all duration-200 cursor-pointer" : ""}
                     ${className}`}>
      {children}
    </div>
  );
}
