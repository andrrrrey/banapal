// Цвета аватаров менеджеров и инициалы (перенос из прототипа).
const MGR_COLORS: Record<string, string> = {
  "Азалия Хаметова": "#635BFF",
  "Дмитрий Крылов": "#12B76A",
  "Ольга Северцева": "#F79009",
  "Тимур Рахимов": "#1BA9C7",
};

export function avatarColor(name: string): string {
  return MGR_COLORS[name] ?? "#94A0B8";
}

export function initials(name: string): string {
  if (name === "—") return "?";
  return name.split(" ").map((w) => w[0]).slice(0, 2).join("");
}
