import { redirect } from "next/navigation";
import CustomerShell from "@/components/CustomerShell";
import { getCurrentUser } from "@/lib/backend";

export default async function Home() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  if (user.role === "chef") redirect("/chef");

  return <CustomerShell user={user} />;
}
