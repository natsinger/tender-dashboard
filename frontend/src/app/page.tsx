/**
 * Root page — redirects to the management dashboard (default view).
 */
import { redirect } from "next/navigation";

export default function HomePage() {
  redirect("/management");
}
