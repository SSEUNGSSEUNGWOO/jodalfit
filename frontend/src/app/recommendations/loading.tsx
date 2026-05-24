import { Loader2 } from "lucide-react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export default function Loading() {
  return (
    <>
      <Header />
      <main className="flex-1">
        <div className="mx-auto max-w-[640px] px-5 py-24 sm:py-28 text-center">
          <Loader2 className="mx-auto h-7 w-7 animate-spin text-brand" aria-hidden />
          <p className="mt-6 text-[15.5px] text-ink-3">
            과거 낙찰 이력을 분석하는 중...
          </p>
          <p className="mt-1.5 text-[12.5px] text-ink-5">보통 5~12초 걸려요</p>
        </div>
      </main>
      <Footer />
    </>
  );
}
