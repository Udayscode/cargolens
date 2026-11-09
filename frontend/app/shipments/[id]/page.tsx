"use client";
import Link from "next/link";
import { ChangeEvent, useEffect, useState } from "react";
import {
  ArrowLeft,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Download,
  RefreshCw,
  Upload,
  Eye,
  FileCheck2,
  Info,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

type Field = {
  id: string;
  document_id: string | null;
  name: string;
  value: string | null;
  confidence: number;
  page: number | null;
  verified: boolean;
};

type Validation = {
  id: string;
  rule: string;
  severity: string;
  status: string;
  details: Record<string, any>;
  resolution: string | null;
};

type DocInfo = {
  id: string;
  kind: string;
  filename: string;
  extraction_status: string;
};

type Detail = {
  id: string;
  reference: string;
  supplier: string;
  supplier_country?: string;
  status: string;
  approval_status: string;
  documents: DocInfo[];
  fields: Field[];
  validations: Validation[];
  line_items: Array<{
    id: string;
    description: string;
    quantity: number;
    unit_price: number;
    amount: number;
  }>;
};

export default function Review({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [id, setId] = useState("");
  const [shipment, setShipment] = useState<Detail | null>(null);
  const [activeDocKind, setActiveDocKind] = useState<string>("invoice");
  const [editingFieldId, setEditingFieldId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  const role =
    typeof window === "undefined"
      ? ""
      : localStorage.getItem("role") || "executive";
  const token =
    typeof window === "undefined" ? "" : localStorage.getItem("token") || "";

  const loadShipment = async (shipmentId: string) => {
    try {
      const res = await fetch(`${API}/shipments/${shipmentId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok)
        throw new Error(data.detail || "Could not load shipment details");
      setShipment(data);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load shipment");
    }
  };

  useEffect(() => {
    params.then((p) => {
      setId(p.id);
      loadShipment(p.id);
    });
  }, [params]);

  async function apiAction(path: string, options: RequestInit = {}) {
    setIsProcessing(true);
    try {
      const res = await fetch(API + path, {
        ...options,
        headers: {
          Authorization: `Bearer ${token}`,
          ...(options.headers || {}),
        },
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.detail || "Action failed");
      setNote("Action updated successfully.");
      setTimeout(() => setNote(""), 4000);
      if (id) await loadShipment(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
      setTimeout(() => setError(""), 5000);
    } finally {
      setIsProcessing(false);
    }
  }

  function handleUpload(kind: string) {
    return async (e: ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const formData = new FormData();
      formData.append("document", file);
      setActiveDocKind(kind);
      await apiAction(`/shipments/${id}/documents?kind=${kind}`, {
        method: "POST",
        body: formData,
      });
    };
  }

  async function saveFieldCorrection(fieldId: string) {
    await apiAction(`/fields/${fieldId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        value: editValue,
        reason: "Field verified by documentation executive",
      }),
    });
    setEditingFieldId(null);
  }

  const activeDoc = shipment?.documents.find((d) => d.kind === activeDocKind);
  const activeDocFields = shipment?.fields || [];
  const openViolations =
    shipment?.validations.filter((v) => v.status === "open") || [];
  const lowConfidenceCount =
    shipment?.fields.filter((f) => f.confidence < 0.8 && !f.verified).length ||
    0;

  if (!shipment) {
    return (
      <main className="workspace" style={{ padding: 40, textAlign: "center" }}>
        <p>Loading shipment workspace...</p>
      </main>
    );
  }

  return (
    <main
      className="workspace"
      style={{ maxWidth: "1440px", margin: "0 auto", padding: "24px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <Link
          href="/"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontWeight: 500,
          }}
        >
          <ArrowLeft size={16} /> Back to Dashboard
        </Link>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <span className="badge" style={{ textTransform: "capitalize" }}>
            Role: {role}
          </span>
          <span
            className={`badge ${shipment.approval_status === "approved" ? "success" : "danger"}`}
          >
            Status: {shipment.approval_status}
          </span>
        </div>
      </div>

      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: 16,
          marginBottom: 20,
        }}
      >
        <div>
          <p className="eyebrow" style={{ margin: 0 }}>
            Customs Clearance & Document Audit
          </p>
          <h1 style={{ margin: "4px 0 6px", fontSize: 26 }}>
            {shipment.reference} · {shipment.supplier}
          </h1>
          <p className="muted" style={{ margin: 0, fontSize: 14 }}>
            Port of Discharge: Nhava Sheva (INNSA) | Origin:{" "}
            {shipment.supplier_country || "China"}
          </p>
        </div>

        <div
          className="actions"
          style={{ display: "flex", gap: 10, alignItems: "center" }}
        >
          <button
            onClick={() =>
              apiAction(`/shipments/${id}/validate`, { method: "POST" })
            }
            style={{ display: "flex", alignItems: "center", gap: 6 }}
            disabled={isProcessing}
          >
            <RefreshCw size={15} /> Run Cross-Checks
          </button>

          {role === "manager" && (
            <button
              onClick={() =>
                apiAction(`/shipments/${id}/approve`, { method: "POST" })
              }
              style={{ display: "flex", alignItems: "center", gap: 6 }}
              disabled={
                isProcessing ||
                openViolations.length > 0 ||
                lowConfidenceCount > 0
              }
              title={
                openViolations.length > 0 ? "Resolve open mismatches first" : ""
              }
            >
              <ShieldCheck size={16} /> Approve Filing
            </button>
          )}

          {role === "manager" && (
            <button
              className="primary"
              style={{ display: "flex", alignItems: "center", gap: 6 }}
              disabled={shipment.approval_status !== "approved"}
              onClick={async () => {
                const r = await fetch(`${API}/shipments/${id}/export`, {
                  headers: { Authorization: `Bearer ${token}` },
                });
                if (!r.ok) {
                  const b = await r.json();
                  setError(b.detail || "Export failed");
                  return;
                }
                const blob = await r.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `customs_filing_${shipment.reference}.csv`;
                a.click();
                URL.revokeObjectURL(url);
              }}
            >
              <Download size={16} /> Export ICEGATE CSV
            </button>
          )}
        </div>
      </header>

      {note && (
        <div className="notice success" style={{ marginBottom: 16 }}>
          {note}
        </div>
      )}
      {error && (
        <div className="notice error" style={{ marginBottom: 16 }}>
          {error}
        </div>
      )}

      {/* Discrepancy Alert Banner */}
      {openViolations.length > 0 && (
        <div
          style={{
            background: "#fffbeb",
            border: "1px solid #fde68a",
            borderRadius: 8,
            padding: "14px 18px",
            marginBottom: 20,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              color: "#b45309",
              fontWeight: 600,
            }}
          >
            <AlertTriangle size={18} /> Cross-Check Warning:{" "}
            {openViolations.length} unresolved document mismatch(es) detected!
          </div>
          <p style={{ margin: "6px 0 10px", fontSize: 13, color: "#78350f" }}>
            Per client standard operating procedure, Bill of Entry filing cannot
            be approved until all weight and arithmetic differences are
            verified.
          </p>
          <div style={{ display: "grid", gap: 8 }}>
            {openViolations.map((v) => (
              <div
                key={v.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  background: "#fff",
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid #fed7aa",
                }}
              >
                <span style={{ fontSize: 13, fontWeight: 500 }}>
                  <b>{v.rule.replaceAll("_", " ").toUpperCase()}:</b>{" "}
                  {JSON.stringify(v.details)}
                </span>
                <button
                  style={{ fontSize: 12, padding: "4px 10px" }}
                  onClick={() => {
                    const resText = prompt(
                      `Enter documented resolution for '${v.rule}':`,
                      "Verified against packing slip signed copy; packing weight accepted.",
                    );
                    if (resText) {
                      apiAction(`/validations/${v.id}/resolve`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ resolution: resText }),
                      });
                    }
                  }}
                >
                  Resolve Discrepancy
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Document Selector Bar */}
      <div
        style={{
          display: "flex",
          gap: 10,
          marginBottom: 16,
          borderBottom: "1px solid #e2e8f0",
          paddingBottom: 12,
        }}
      >
        {(["invoice", "packing_list", "bill_of_lading"] as const).map(
          (kind) => {
            const doc = shipment.documents.find((d) => d.kind === kind);
            const isActive = activeDocKind === kind;
            return (
              <div
                key={kind}
                onClick={() => setActiveDocKind(kind)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "8px 14px",
                  borderRadius: 6,
                  cursor: "pointer",
                  background: isActive ? "#1e293b" : "#fff",
                  color: isActive ? "#fff" : "#475569",
                  border: "1px solid",
                  borderColor: isActive ? "#1e293b" : "#cbd5e1",
                  fontWeight: 500,
                  fontSize: 13,
                }}
              >
                <FileText size={15} />
                <span style={{ textTransform: "capitalize" }}>
                  {kind.replaceAll("_", " ")}
                </span>
                {doc ? (
                  <span
                    style={{
                      fontSize: 11,
                      background: isActive ? "#334155" : "#e2e8f0",
                      padding: "2px 6px",
                      borderRadius: 4,
                    }}
                  >
                    Uploaded
                  </span>
                ) : (
                  <span style={{ fontSize: 11, color: "#ef4444" }}>
                    Missing
                  </span>
                )}
              </div>
            );
          },
        )}
      </div>

      {/* Side-by-Side Review Grid */}
      <div
        style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 20 }}
      >
        {/* Left: Document Viewer */}
        <section
          className="card"
          style={{
            padding: 18,
            minHeight: "620px",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 12,
            }}
          >
            <h2
              style={{ fontSize: 17, margin: 0, textTransform: "capitalize" }}
            >
              {activeDocKind.replaceAll("_", " ")} Document Viewer
            </h2>
            <label
              className="button"
              style={{
                fontSize: 12,
                padding: "5px 10px",
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              <Upload size={13} /> {activeDoc ? "Replace PDF" : "Upload PDF"}
              <input
                type="file"
                accept="application/pdf"
                onChange={handleUpload(activeDocKind)}
                style={{ display: "none" }}
              />
            </label>
          </div>

          {activeDoc ? (
            <div
              style={{
                flex: 1,
                border: "1px solid #cbd5e1",
                borderRadius: 6,
                overflow: "hidden",
                minHeight: "520px",
                background: "#f8fafc",
              }}
            >
              <iframe
                src={`${API}/documents/${activeDoc.id}/file`}
                style={{
                  width: "100%",
                  height: "100%",
                  minHeight: "560px",
                  border: "none",
                }}
                title="Document Preview"
              />
            </div>
          ) : (
            <div
              style={{
                flex: 1,
                display: "grid",
                placeItems: "center",
                border: "2px dashed #cbd5e1",
                borderRadius: 8,
                padding: 40,
                textAlign: "center",
              }}
            >
              <div>
                <FileText
                  size={40}
                  style={{ color: "#94a3b8", margin: "0 auto 12px" }}
                />
                <h3 style={{ margin: "0 0 6px", fontSize: 16 }}>
                  No {activeDocKind.replaceAll("_", " ")} uploaded
                </h3>
                <p className="muted" style={{ fontSize: 13, marginBottom: 16 }}>
                  Upload a PDF copy to automatically trigger AI extraction and
                  cross-checking.
                </p>
                <label
                  className="primary button"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: 13,
                  }}
                >
                  <Upload size={14} /> Upload{" "}
                  {activeDocKind.replaceAll("_", " ")}
                  <input
                    type="file"
                    accept="application/pdf"
                    onChange={handleUpload(activeDocKind)}
                    style={{ display: "none" }}
                  />
                </label>
              </div>
            </div>
          )}
        </section>

        {/* Right: Extracted Fields & Discrepancies */}
        <section
          className="card"
          style={{ padding: 18, overflowY: "auto", maxHeight: "720px" }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 14,
            }}
          >
            <h2 style={{ fontSize: 17, margin: 0 }}>
              AI Extracted Fields & Confidence
            </h2>
            <span style={{ fontSize: 12, color: "#64748b" }}>
              {lowConfidenceCount > 0 ? (
                <span style={{ color: "#b45309", fontWeight: 600 }}>
                  ⚠️ {lowConfidenceCount} Needs Verification
                </span>
              ) : (
                <span style={{ color: "#16a34a", fontWeight: 600 }}>
                  ✓ All Fields Verified
                </span>
              )}
            </span>
          </div>

          <div style={{ display: "grid", gap: 12 }}>
            {activeDocFields.length === 0 ? (
              <p className="muted" style={{ fontSize: 13 }}>
                No extracted fields yet. Upload a PDF to trigger extraction.
              </p>
            ) : (
              activeDocFields.map((f) => {
                const isLow = f.confidence < 0.8 && !f.verified;
                const isEditing = editingFieldId === f.id;

                return (
                  <div
                    key={f.id}
                    style={{
                      padding: "10px 14px",
                      borderRadius: 6,
                      border: "1px solid",
                      borderColor: isLow ? "#fcd34d" : "#e2e8f0",
                      background: isLow ? "#fffbeb" : "#fff",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: 6,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 12,
                          textTransform: "uppercase",
                          letterSpacing: "0.05em",
                          fontWeight: 600,
                          color: "#475569",
                        }}
                      >
                        {f.name.replaceAll("_", " ")}
                      </span>
                      <div
                        style={{
                          display: "flex",
                          gap: 6,
                          alignItems: "center",
                        }}
                      >
                        {f.verified && (
                          <span
                            className="badge success"
                            style={{ fontSize: 11 }}
                          >
                            ✓ Verified
                          </span>
                        )}
                        <span
                          className={`badge ${f.confidence >= 0.8 ? "success" : "danger"}`}
                          style={{ fontSize: 11 }}
                        >
                          {Math.round(f.confidence * 100)}% conf · Page{" "}
                          {f.page || 1}
                        </span>
                      </div>
                    </div>

                    {isEditing ? (
                      <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                        <input
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          style={{
                            flex: 1,
                            padding: "6px 10px",
                            fontSize: 14,
                            borderRadius: 5,
                            border: "1px solid #3b82f6",
                          }}
                          autoFocus
                        />
                        <button
                          className="primary"
                          style={{ fontSize: 12, padding: "6px 12px" }}
                          onClick={() => saveFieldCorrection(f.id)}
                        >
                          Confirm
                        </button>
                        <button
                          style={{ fontSize: 12, padding: "6px 10px" }}
                          onClick={() => setEditingFieldId(null)}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <span
                          style={{
                            fontSize: 14,
                            fontWeight: 600,
                            color: "#1e293b",
                          }}
                        >
                          {f.value || <i style={{ color: "#94a3b8" }}>Empty</i>}
                        </span>
                        <button
                          style={{
                            fontSize: 12,
                            padding: "3px 8px",
                            color: "#2563eb",
                          }}
                          onClick={() => {
                            setEditingFieldId(f.id);
                            setEditValue(f.value || "");
                          }}
                        >
                          Edit
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Line Items Breakdown */}
          {shipment.line_items.length > 0 && (
            <div
              style={{
                marginTop: 22,
                borderTop: "1px solid #e2e8f0",
                paddingTop: 14,
              }}
            >
              <h3 style={{ fontSize: 15, margin: "0 0 10px" }}>
                Invoice Line Items
              </h3>
              <table style={{ width: "100%", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                    <th style={{ padding: "6px 8px" }}>Description</th>
                    <th style={{ padding: "6px 8px" }}>Qty</th>
                    <th style={{ padding: "6px 8px" }}>Unit Price</th>
                    <th style={{ padding: "6px 8px" }}>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {shipment.line_items.map((item) => (
                    <tr
                      key={item.id}
                      style={{ borderBottom: "1px solid #f1f5f9" }}
                    >
                      <td style={{ padding: "6px 8px" }}>{item.description}</td>
                      <td style={{ padding: "6px 8px" }}>{item.quantity}</td>
                      <td style={{ padding: "6px 8px" }}>
                        ${item.unit_price.toFixed(2)}
                      </td>
                      <td style={{ padding: "6px 8px", fontWeight: 600 }}>
                        ${item.amount.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
