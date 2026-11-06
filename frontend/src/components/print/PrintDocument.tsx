import { API_URL } from "@/services/api";

export function PrintDocument({ pdfPath, children }: { pdfPath: string; children: React.ReactNode }) {
  return (
    <article className="impressao">
      <div className="barra-tela">
        <a href={`${API_URL}/api/v1/export/${pdfPath}.pdf`}>Baixar PDF</a>
        <span>ou use Imprimir do navegador</span>
      </div>
      {children}
    </article>
  );
}
