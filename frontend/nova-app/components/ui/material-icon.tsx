"use client";

interface MaterialIconProps {
  icon: string;
  className?: string;
  filled?: boolean;
}

export function MaterialIcon({ icon, className = "" }: MaterialIconProps) {
  return (
    <span className={`material-icons-outlined ${className}`}>
      {icon}
    </span>
  );
}
