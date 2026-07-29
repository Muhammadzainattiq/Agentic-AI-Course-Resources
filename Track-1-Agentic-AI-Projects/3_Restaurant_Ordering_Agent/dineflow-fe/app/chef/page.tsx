import Image from "next/image";
import { redirect } from "next/navigation";
import AccountMenu from "@/components/AccountMenu";
import ChefBoard from "@/components/ChefBoard";
import { getCurrentUser } from "@/lib/backend";

export const metadata = { title: "Kitchen — DineFlow" };

export default async function ChefPage() {
  const user = await getCurrentUser();

  // Guarded server-side: a customer can't reach the kitchen by typing the URL,
  // and the backend rejects their token on /kitchen/* regardless.
  if (!user) redirect("/login");
  if (user.role !== "chef") redirect("/");

  return (
    <main className="flex flex-1 flex-col">
      <header className="flex items-center justify-between gap-3 border-b border-neutral-200 px-6 py-4 dark:border-neutral-800">
        <div className="flex items-center gap-3">
          <Image
            src="/logo-mark.png"
            alt=""
            width={512}
            height={512}
            priority
            className="size-11 shrink-0 rounded-full bg-cream ring-1 ring-neutral-200 dark:ring-neutral-700"
          />
          <div>
            <h1 className="text-lg font-semibold tracking-tight">
              Dine<span className="text-brand">Flow</span> Kitchen
            </h1>
            <p className="text-xs text-neutral-500">
              Every order, live. Move tickets through the line.
            </p>
          </div>
        </div>
        <AccountMenu user={user} />
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <ChefBoard />
      </div>
    </main>
  );
}
