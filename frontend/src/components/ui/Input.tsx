import { forwardRef, InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, leftIcon, rightIcon, className = "", ...rest }, ref) => (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-slate-300 mb-1.5">{label}</label>
      )}
      <div className="relative">
        {leftIcon && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">{leftIcon}</span>
        )}
        <input
          ref={ref}
          className={`w-full bg-slate-800 border text-white placeholder-slate-500 rounded-xl
                      px-4 py-2.5 text-sm transition focus:outline-none focus:ring-2
                      min-h-[44px]
                      ${error ? "border-red-500 focus:ring-red-500" : "border-slate-600 focus:ring-blue-500 focus:border-blue-500"}
                      ${leftIcon ? "pl-10" : ""}
                      ${rightIcon ? "pr-10" : ""}
                      ${className}`}
          {...rest}
        />
        {rightIcon && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">{rightIcon}</span>
        )}
      </div>
      {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
      {hint && !error && <p className="text-slate-500 text-xs mt-1">{hint}</p>}
    </div>
  )
);
Input.displayName = "Input";
export default Input;
