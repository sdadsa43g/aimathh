import { useEffect, useRef } from "react";
import katex from "katex";

/** KaTeX equation renderer. Swap this file to use MathJax instead —
 *  the rest of the UI only depends on this component's props. */
export default function Equation({ latex, block = false }: { latex: string; block?: boolean }) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (ref.current) {
      try {
        katex.render(latex, ref.current, { displayMode: block, throwOnError: false });
      } catch {
        if (ref.current) ref.current.textContent = latex;
      }
    }
  }, [latex, block]);
  return block ? (
    <div className="overflow-x-auto py-1">
      <span ref={ref} />
    </div>
  ) : (
    <span ref={ref} />
  );
}
