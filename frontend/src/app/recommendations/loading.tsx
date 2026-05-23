import { Loader2 } from "lucide-react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export default function Loading() {
  return (
    <>
      <Header />
      <main className="flex-1">
        <div className="mx-auto max-w-[1180px] px-6 py-20 text-center sm:px-8 sm:py-28">
          <Loader2 className="mx-auto h-7 w-7 animate-spin text-teal-500" aria-hidden />
          <p className="mt-5 text-[15px] text-ink-muted">
            과거 낙찰 이력을 분석하는 중...
          </p>
          <p className="mt-1 text-[12.5px] tabular text-ink-soft">
            보통 2~5초가 걸립니다
          </p>
        </div>
      </main>
      <Footer />
    </>
  );
}
