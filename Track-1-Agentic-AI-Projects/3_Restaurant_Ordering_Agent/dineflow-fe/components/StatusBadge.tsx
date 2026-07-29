import { STATUS_LABEL, type OrderStatus } from "@/lib/api";

const STYLES: Record<OrderStatus, string> = {
  pending:
    "bg-neutral-200 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300",
  baking: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  baked: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  in_delivery:
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  cancelled: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
};

export default function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${STYLES[status]}`}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}
