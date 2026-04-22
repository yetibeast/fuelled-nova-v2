"use client";

import Link from "next/link";
import { MaterialIcon } from "@/components/ui/material-icon";
import { WorkedExample } from "@/components/methodology/worked-example";

export default function MethodologyExamplePage() {
  return (
    <>
      <div className="mb-6">
        <Link
          href="/methodology"
          className="text-[11px] font-mono text-on-surface/40 hover:text-on-surface/70 flex items-center gap-1 mb-3 transition-colors w-fit"
        >
          <MaterialIcon icon="arrow_back" className="text-[14px]" />
          Back to methodology
        </Link>
        <h1 className="font-headline font-bold text-xl tracking-tight">Worked Example</h1>
        <p className="text-on-surface/40 text-xs font-mono mt-1">
          A generalized compressor package carried through every stage of the pipeline
        </p>
      </div>

      <WorkedExample />
    </>
  );
}
