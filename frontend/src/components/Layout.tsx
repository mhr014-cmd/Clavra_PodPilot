import Sidebar from "./Sidebar";
import Navbar  from "./Navbar";

interface Props { children: React.ReactNode; }

export default function Layout({ children }: Props) {
  return (
    <div className="flex bg-slate-950 min-h-screen text-white">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-auto bg-slate-950">
          {children}
        </main>
      </div>
    </div>
  );
}
