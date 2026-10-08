import { useState, type ReactNode } from "react";

type Props = {
  context: string;
  summary: string;
  children: (visible: boolean) => ReactNode;
};
/** Native disclosure; retain opened editor state until its actual context changes. */
export function DeferredPanel({ context, ...props }: Props) {
  return <ScopedPanel key={context} {...props} />;
}
function ScopedPanel({ summary, children }: Omit<Props, "context">) {
  const [activated, setActivated] = useState(false);
  const [visible, setVisible] = useState(false);
  return (
    <details
      className="panel"
      onToggle={(event) => {
        const open = event.currentTarget.open;
        setVisible(open);
        if (open) setActivated(true);
      }}
    >
      <summary>{summary}</summary>
      {activated && children(visible)}
    </details>
  );
}
