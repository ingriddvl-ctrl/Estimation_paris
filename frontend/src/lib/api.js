import { useState, useEffect, useRef } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Upload, FileText, Image, Trash2, Download, Loader2, FolderOpen, Search, AlertTriangle, AlertCircle, Info } from "lucide-react";

const CATEGORIES = [
  { value: "pv_ag", label: "PV d'Assemblée Générale" },
  { value: "releve_charges", label: "Relevé de charges" },
  { value: "dpe", label: "DPE" },
  { value: "diagnostic", label: "Diagnostic technique" },
  { value: "reglement_copro", label: "Règlement de copropriété" },
  { value: "plan", label: "Plan du bien" },
  { value: "photo", label: "Photo" },
  { value: "compromis", label: "Compromis de vente" },
  { value: "autre", label: "Autre document" },
];

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

const FILE_ICONS = {
  "application/pdf": FileText,
  "image/jpeg": Image,
  "image/png": Image,
};

export default function DocumentUpload({ valuationId }) {
  const [docs, setDocs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(null);
  const [category, setCategory] = useState("autre");
  const [loading, setLoading] = useState(true);
  const fileRef = useRef(null);

  useEffect(() => {
    if (valuationId) {
      api.listDocuments(valuationId).then(setDocs).catch(() => {}).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [valuationId]);

  const handleUpload = async (e) => {
    const files = e.target.files;
    if (!files?.length) return;
    setUploading(true);
    try {
      for (const file of files) {
        const result = await api.uploadDocument(file, valuationId, category);
        setDocs(prev => [result, ...prev]);
      }
      toast.success(`${files.length} document(s) ajouté(s)`);
    } catch (err) {
      const msg = err?.response?.data?.detail || "Erreur d'upload";
      toast.error(msg);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleAnalyze = async (doc) => {
    setAnalyzing(doc.id);
    try {
      const result = await api.analyzeDocument(doc.id);
      setDocs(prev => prev.map(d => d.id === doc.id ? { ...d, analysis: result } : d));
      const items = result.detected_items?.length || 0;
      if (items > 0) {
        toast.success(`${items} élément(s) détecté(s) dans le document !`);
      } else {
        toast.info("Aucun risque détecté dans ce document.");
      }
    } catch {
      toast.error("Erreur d'analyse du document");
    } finally {
      setAnalyzing(null);
    }
  };

  const handleDownload = async (doc) => {
    try {
      const resp = await api.downloadDocument(doc.id);
      const url = URL.createObjectURL(resp.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.original_filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Erreur de téléchargement");
    }
  };

  const handleDelete = async (docId) => {
    try {
      await api.deleteDocument(docId);
      setDocs(prev => prev.filter(d => d.id !== docId));
      toast.success("Document supprimé");
    } catch {
      toast.error("Erreur de suppression");
    }
  };

  return (
    <div data-testid="document-upload-panel">
      <p className="text-xs uppercase tracking-[0.2em] text-zinc-400 font-mono mb-4">Documents du bien</p>
      <p className="text-sm text-zinc-500 mb-6">
        Ajoutez vos documents : PV d'AG, relevés de charges, DPE, diagnostics, plans, photos.
        Ces pièces complètent votre dossier de valorisation.
      </p>

      {/* Upload zone */}
      <div className="border border-dashed border-zinc-300 p-6 mb-6 hover:border-zinc-400 transition-colors" data-testid="upload-zone">
        <div className="flex flex-col sm:flex-row items-center gap-4">
          <div className="flex-1 flex items-center gap-4">
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger className="rounded-none h-10 w-56" data-testid="doc-category-select">
                <SelectValue placeholder="Catégorie" />
              </SelectTrigger>
              <SelectContent>
                {CATEGORIES.map(c => (
                  <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <input
              ref={fileRef}
              type="file"
              multiple
              accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx,.txt,.csv"
              className="hidden"
              onChange={handleUpload}
              data-testid="file-input"
            />
            <Button
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              variant="outline"
              className="rounded-none h-10"
              data-testid="upload-btn"
            >
              {uploading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Upload className="w-4 h-4 mr-2" />}
              {uploading ? "Upload..." : "Choisir des fichiers"}
            </Button>
          </div>
          <p className="text-xs text-zinc-400">PDF, images, Excel — max 20 Mo</p>
        </div>
      </div>

      {/* Document list */}
      {loading ? (
        <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-zinc-300" /></div>
      ) : docs.length === 0 ? (
        <div className="border border-zinc-200 p-8 text-center" data-testid="no-documents">
          <FolderOpen className="w-6 h-6 text-zinc-300 mx-auto mb-3" />
          <p className="text-sm text-zinc-400">Aucun document ajouté</p>
        </div>
      ) : (
        <div className="space-y-px bg-zinc-200" data-testid="documents-list">
          {docs.map((doc, i) => {
            const Icon = FILE_ICONS[doc.content_type] || FileText;
            return (
              <div key={doc.id} className="bg-white px-5 py-3" data-testid={`doc-item-${i}`}>
                <div className="flex items-center justify-between hover:bg-zinc-50 transition-colors">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <Icon className="w-4 h-4 text-zinc-400 shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{doc.original_filename}</p>
                      <div className="flex items-center gap-2 text-xs text-zinc-400">
                        <span className="px-1.5 py-0.5 bg-zinc-100 font-mono">{doc.category_label || doc.category}</span>
                        <span>{formatSize(doc.size)}</span>
                        <span>{new Date(doc.created_at).toLocaleDateString("fr-FR")}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0 ml-2">
                    {(doc.category === "pv_ag" || doc.category === "releve_charges" || doc.category === "diagnostic") && !doc.analysis && (
                      <Button variant="outline" size="sm" onClick={() => handleAnalyze(doc)} disabled={analyzing === doc.id} className="rounded-none h-8 text-xs px-2">
                        {analyzing === doc.id ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Search className="w-3 h-3 mr-1" />}
                        Analyser
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" onClick={() => handleDownload(doc)} className="rounded-none h-8 w-8 p-0" data-testid={`doc-download-${i}`}>
                      <Download className="w-3.5 h-3.5" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(doc.id)} className="rounded-none h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50" data-testid={`doc-delete-${i}`}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
                {/* Analysis results */}
                {doc.analysis?.detected_items?.length > 0 && (
                  <div className="mt-3 ml-7 space-y-2">
                    {doc.analysis.detected_items.map((item, j) => {
                      const ItemIcon = item.level === "critical" ? AlertCircle : item.level === "warning" ? AlertTriangle : Info;
                      const colors = item.level === "critical" ? "bg-red-50 border-red-200 text-red-800" : item.level === "warning" ? "bg-amber-50 border-amber-200 text-amber-800" : "bg-blue-50 border-blue-200 text-blue-800";
                      return (
                        <div key={j} className={`p-3 border text-xs ${colors}`}>
                          <div className="flex items-center gap-2 font-medium mb-1">
                            <ItemIcon className="w-3.5 h-3.5" />
                            {item.label}
                          </div>
                          <p className="opacity-80">{item.detail}</p>
                        </div>
                      );
                    })}
                  </div>
                )}
                {doc.analysis && doc.analysis.detected_items?.length === 0 && (
                  <div className="mt-3 ml-7 p-3 bg-green-50 border border-green-200 text-xs text-green-800">
                    Aucun risque détecté dans ce document.
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
