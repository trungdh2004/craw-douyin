import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"
import { Slot } from "radix-ui"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-lg border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-colors outline-none select-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40 active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-45 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-primary text-primary-foreground hover:bg-primary/90",
        outline:
          "border-border bg-card hover:bg-muted/70 text-foreground",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-foreground/[0.08]",
        ghost:
          "text-muted-foreground hover:bg-foreground/[0.05] hover:text-foreground",
        destructive:
          "bg-destructive/10 text-destructive border-destructive/20 hover:bg-destructive/15",
        link: "text-foreground underline-offset-4 hover:underline",
      },
      size: {
        default:
          "h-8 min-h-[28px] gap-1.5 px-3",
        xs: "h-7 min-h-[28px] gap-1 rounded-md px-2 text-xs [&_svg:not([class*='size-'])]:size-3.5",
        sm: "h-7 min-h-[28px] gap-1.5 rounded-lg px-2.5 text-xs [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-9 gap-2 px-3.5",
        icon: "size-8 min-w-[28px] min-h-[28px]",
        "icon-xs":
          "size-7 min-w-[28px] min-h-[28px] rounded-md [&_svg:not([class*='size-'])]:size-3.5",
        "icon-sm":
          "size-7 min-w-[28px] min-h-[28px] rounded-lg",
        "icon-lg": "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
