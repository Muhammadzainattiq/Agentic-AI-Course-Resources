import { redirect } from "next/navigation";
import AuthForm from "@/components/AuthForm";
import { getCurrentUser } from "@/lib/backend";

export const metadata = { title: "Create account — DineFlow" };

export default async function SignupPage() {
  const user = await getCurrentUser();
  if (user) redirect(user.role === "chef" ? "/chef" : "/");
  return <AuthForm mode="signup" />;
}
