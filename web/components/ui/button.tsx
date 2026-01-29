import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--oai-primary)] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--oai-primary)] text-[var(--oai-bg)] hover:bg-[var(--oai-primary)]/90 shadow-sm hover:shadow-md",
        destructive:
          "bg-[var(--oai-error)] text-white hover:bg-[var(--oai-error)]/90",
        outline:
          "border border-[var(--oai-border)] bg-transparent hover:bg-[var(--oai-surface-light)] hover:text-[var(--oai-primary)]",
        secondary:
          "bg-[var(--oai-secondary)] text-white hover:bg-[var(--oai-secondary)]/80",
        ghost:
          "hover:bg-[var(--oai-surface-light)] hover:text-[var(--oai-primary)]",
        link: "text-[var(--oai-primary)] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
