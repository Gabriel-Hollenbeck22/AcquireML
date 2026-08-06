export interface Command {
  id: string;
  label: string;
  action: () => void;
}

export function filterCommands(commands: Command[], query: string): Command[] {
  const trimmed = query.trim().toLowerCase();
  if (trimmed === "") return commands;

  return commands
    .map((cmd) => ({ cmd, index: cmd.label.toLowerCase().indexOf(trimmed) }))
    .filter(({ index }) => index !== -1)
    .sort((a, b) => a.index - b.index)
    .map(({ cmd }) => cmd);
}
