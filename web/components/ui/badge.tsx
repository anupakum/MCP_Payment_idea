import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--oai-primary)] focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-[var(--oai-primary)] text-[var(--oai-bg)] hover:bg-[var(--oai-primary)]/90",
        secondary:
          "border-transparent bg-[var(--oai-secondary)] text-white hover:bg-[var(--oai-secondary)]/80",
        destructive:
          "border-transparent bg-[var(--oai-error)] text-white hover:bg-[var(--oai-error)]/80",
        success:
          "border-transparent bg-[var(--oai-success)] text-white hover:bg-[var(--oai-success)]/90",
        warning:
          "border-transparent bg-[var(--oai-warning)] text-white hover:bg-[var(--oai-warning)]/90",
        outline: "border-[var(--oai-border)] text-[var(--oai-text)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
