import type { SVGProps } from "react";

export type IconName =
  | "bars"
  | "close"
  | "new"
  | "trash"
  | "send"
  | "stop"
  | "user"
  | "advisor"
  | "edit"
  | "chevron";

interface IconProps extends SVGProps<SVGSVGElement> {
  name: IconName;
  size?: number;
}

const paths: Record<IconName, string> = {
  bars: "M4 7h16M4 12h16M4 17h16",
  close: "M6 6l12 12M18 6 6 18",
  new: "M12 5v14M5 12h14",
  trash:
    "M5 7h14M9 7V4h6v3M8 10v8m4-8v8m4-8v8M6 7l1 14h10l1-14",
  send: "M3.5 4.5l17 7.5-17 7.5 3-7.5-3-7.5Zm3 7.5h8",
  stop: "M7 7h10v10H7z",
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm7 8a7 7 0 0 0-14 0",
  advisor:
    "M4 17V7l8-4 8 4v10l-8 4-8-4Zm4-7h8M8 14h5M8 7v10M16 7v10",
  edit: "M4 20h4L19 9l-4-4L4 16v4Zm9-13 4 4",
  chevron: "m8 10 4 4 4-4",
};

export function Icon({
  name,
  size = 20,
  className,
  ...props
}: IconProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      {...props}
    >
      <path
        d={paths[name]}
        stroke="currentColor"
        strokeLinecap="square"
        strokeLinejoin="miter"
        strokeWidth="1.8"
      />
    </svg>
  );
}
