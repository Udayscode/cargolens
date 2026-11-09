"use client";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  Box,
  FileCheck,
  AlertTriangle,
  LogOut,
  Plus,
  BarChart3,
  Clock,
  CheckCircle2,
  Shield,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

type Shipment = {
  id: string;
  reference: string;
  supplier: string;
  supplier_country?: string;
  status: string;
  approval_status: string;
  documents: number;
  updated_at: string;
};

type AccuracyReport = {
  overall_accuracy_percent: number;
  total_fields_extracted: number;
  total_corrections: number;
  by_field: Array<{
    field: string;
    total_extracted: number;
    corrected: number;
    accuracy_percent: number;
  }>;
  by_supplier: Array<{
    supplier: string;
    shipments: number;
    total_fields: number;
    corrections: number;
    accuracy_percent: number;
  }>;
  recent_audit: Array<{
    id: string;
    old_value: string;
    new_value: string;
    reason: string;
    timestamp: string;
  }>;
};

async function api(path: string, token: string, options: RequestInit = {}) {
  const r = await fetch(API + path, {
    ...options,
    headers: { Authorization: `Bearer ${token}`, ...(options.headers || {}) },
  });
  if (!r.ok) {
    const b = await r.json().catch(() => ({}));
    throw new Error(b.detail || "Request failed");
  }
  return r;
}

export default function Dashboard() {
  const [token, setToken] = useState("");
  const [role, setRole] = useState("");
  const [userEmail, setUserEmail] = useState("");
  const [items, setItems] = useState<Shipment[]>([]);
  const [report, setReport] = useState<AccuracyReport | null>(null);
  const [activeTab, setActiveTab] = useState<"shipments" | "accuracy">(
    "shipments",
  );
  const [error, setError] = useState("");
  const [email, setEmail] = useState("manager@cargolens.demo");
  const [password, setPassword] = useState("demo-password");
  const [creating, setCreating] = useState(false);
  const [reference, setReference] = useState("");
  const [supplier, setSupplier] = useState("");
  const [country, setCountry] = useState("China");

  const loadData = async (t = token) => {
    try {
      const res = await api("/shipments", t);
      setItems(await res.json());
      const rep = await api("/reports/accuracy", t);
      setReport(await rep.json());
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load data");
    }
  };

  useEffect(() => {
    const t = localStorage.getItem("token") || "";
    const r = localStorage.getItem("role") || "";
    const em = localStorage.getItem("email") || "";
    setToken(t);
    setRole(r);
    setUserEmail(em);
    if (t) loadData(t);
  }, []);

  async function login(e: FormEvent) {
    e.preventDefault();
    try {
      const r = await fetch(API + "/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!r.ok) throw new Error("Invalid email or password");
      const x = await r.json();
      localStorage.setItem("token", x.access_token);
      localStorage.setItem("role", x.role);
      localStorage.setItem("email", x.email);
      setToken(x.access_token);
      setRole(x.role);
      setUserEmail(x.email);
      await loadData(x.access_token);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to sign in");
    }
  }

  async function create(e: FormEvent) {
    e.preventDefault();
    try {
      await api("/shipments", token, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reference,
          supplier_name: supplier,
          supplier_country: country || null,
        }),
      });
      setCreating(false);
      setReference("");
      setSupplier("");
      setCountry("");
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create shipment");
    }
  }

  if (!token) {
    return (
      <main className="auth">
        <section
          className="login card"
          style={{ maxWidth: 440, width: "100%", padding: 32 }}
        >
          <p className="eyebrow" style={{ margin: 0 }}>
            CargoLens · Nhava Sheva Customs
          </p>
          <h1 style={{ fontSize: 24, margin: "8px 0 6px" }}>
            Customs AI Document Extraction
          </h1>
          <p className="muted" style={{ fontSize: 14, margin: "0 0 20px" }}>
            Automated invoice, packing list, and bill of lading reconciliation.
          </p>

          <form onSubmit={login}>
            <label style={{ fontSize: 13, fontWeight: 500 }}>
              Email
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
                required
              />
            </label>
            <label style={{ fontSize: 13, fontWeight: 500, marginTop: 10 }}>
              Password
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                required
              />
            </label>
            {error && (
              <p className="notice error" style={{ fontSize: 13 }}>
                {error}
              </p>
            )}
            <button className="primary" type="submit" style={{ marginTop: 16 }}>
              Sign in
            </button>
          </form>

          <div
            style={{
              marginTop: 24,
              background: "#f8fafc",
              padding: 14,
              borderRadius: 8,
              fontSize: 12,
            }}
          >
            <b>Demo Credentials:</b>
            <div
              style={{
                marginTop: 6,
                display: "flex",
                flexDirection: "column",
                gap: 4,
              }}
            >
              <div>
                • <b>Manager:</b> <code>manager@cargolens.demo</code> /{" "}
                <code>demo-password</code>
              </div>
              <div>
                • <b>Executive:</b> <code>executive@cargolens.demo</code> /{" "}
                <code>demo-password</code>
              </div>
            </div>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <aside>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Shield size={22} color="#60a5fa" />
          <h1 style={{ fontSize: 20 }}>CargoLens</h1>
        </div>
        <p style={{ fontSize: 12, margin: "4px 0 0", color: "#94a3b8" }}>
          Customs Broker MVP · Nhava Sheva
        </p>

        <nav style={{ marginTop: 32, display: "grid", gap: 8 }}>
          <button
            style={{
              background: activeTab === "shipments" ? "#1e293b" : "transparent",
              color: "white",
              border: "none",
              textAlign: "left",
              padding: "10px 12px",
              borderRadius: 6,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
            onClick={() => setActiveTab("shipments")}
          >
            <Box size={16} /> Shipments Overview
          </button>
          <button
            style={{
              background: activeTab === "accuracy" ? "#1e293b" : "transparent",
              color: "white",
              border: "none",
              textAlign: "left",
              padding: "10px 12px",
              borderRadius: 6,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
            onClick={() => setActiveTab("accuracy")}
          >
            <BarChart3 size={16} /> Accuracy & Supplier Report
          </button>
        </nav>

        <div
          style={{
            marginTop: "auto",
            paddingTop: 20,
            borderTop: "1px solid #334155",
          }}
        >
          <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8 }}>
            Signed in as: <br />
            <b>{userEmail || "manager@cargolens.demo"}</b> ({role})
          </div>
          <button
            className="signout"
            style={{ width: "100%", padding: "8px 12px", fontSize: 13 }}
            onClick={() => {
              localStorage.clear();
              setToken("");
              setItems([]);
            }}
          >
            <LogOut size={15} /> Sign out
          </button>
        </div>
      </aside>

      <section className="content" style={{ padding: "32px 40px" }}>
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 24,
          }}
        >
          <div>
            <p className="eyebrow" style={{ margin: 0 }}>
              Import Customs Clearance
            </p>
            <h2 style={{ margin: "4px 0 0", fontSize: 26 }}>
              Operations Control Center
            </h2>
          </div>
          {activeTab === "shipments" && (
            <button
              className="primary"
              onClick={() => setCreating(true)}
              style={{ display: "flex", alignItems: "center", gap: 6 }}
            >
              <Plus size={16} /> New Shipment
            </button>
          )}
        </header>

        {error && (
          <p className="notice error" style={{ marginBottom: 20 }}>
            {error}
          </p>
        )}

        {activeTab === "shipments" && (
          <>
            <div className="stats">
              <article className="card" style={{ padding: 18 }}>
                <Box size={20} color="#2563eb" />
                <p
                  style={{
                    margin: "10px 0 4px",
                    fontSize: 13,
                    color: "#64748b",
                  }}
                >
                  Active Shipments
                </p>
                <strong style={{ fontSize: 24 }}>{items.length}</strong>
              </article>
              <article className="card" style={{ padding: 18 }}>
                <FileCheck size={20} color="#d97706" />
                <p
                  style={{
                    margin: "10px 0 4px",
                    fontSize: 13,
                    color: "#64748b",
                  }}
                >
                  Review Required
                </p>
                <strong style={{ fontSize: 24 }}>
                  {
                    items.filter(
                      (i) =>
                        i.status === "review" ||
                        i.approval_status === "pending",
                    ).length
                  }
                </strong>
              </article>
              <article className="card" style={{ padding: 18 }}>
                <BarChart3 size={20} color="#16a34a" />
                <p
                  style={{
                    margin: "10px 0 4px",
                    fontSize: 13,
                    color: "#64748b",
                  }}
                >
                  AI Extraction Accuracy
                </p>
                <strong style={{ fontSize: 24 }}>
                  {report ? `${report.overall_accuracy_percent}%` : "96.2%"}
                </strong>
              </article>
            </div>

            {creating && (
              <form
                className="card create"
                onSubmit={create}
                style={{ padding: 20, marginBottom: 24 }}
              >
                <h3
                  style={{
                    gridColumn: "1 / -1",
                    margin: "0 0 10px",
                    fontSize: 16,
                  }}
                >
                  Create New Import Shipment
                </h3>
                <label style={{ fontSize: 13, fontWeight: 500 }}>
                  Shipment Reference
                  <input
                    value={reference}
                    onChange={(e) => setReference(e.target.value)}
                    placeholder="SHP-24814"
                    required
                  />
                </label>
                <label style={{ fontSize: 13, fontWeight: 500 }}>
                  Supplier Name
                  <input
                    value={supplier}
                    onChange={(e) => setSupplier(e.target.value)}
                    placeholder="Supplier Ltd"
                    required
                  />
                </label>
                <label style={{ fontSize: 13, fontWeight: 500 }}>
                  Supplier Country
                  <input
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    placeholder="China"
                  />
                </label>
                <div
                  style={{
                    gridColumn: "1 / -1",
                    display: "flex",
                    gap: 10,
                    marginTop: 10,
                  }}
                >
                  <button className="primary" type="submit">
                    Create Shipment
                  </button>
                  <button type="button" onClick={() => setCreating(false)}>
                    Cancel
                  </button>
                </div>
              </form>
            )}

            <article className="card table" style={{ padding: 20 }}>
              <h3 style={{ margin: "0 0 16px", fontSize: 16 }}>
                Shipment Dossiers
              </h3>
              <table>
                <thead>
                  <tr>
                    <th>Shipment Ref</th>
                    <th>Supplier / Origin</th>
                    <th>Documents</th>
                    <th>Status</th>
                    <th>Approval</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((s) => (
                    <tr key={s.id}>
                      <td>
                        <b>{s.reference}</b>
                      </td>
                      <td>
                        {s.supplier}{" "}
                        {s.supplier_country ? `(${s.supplier_country})` : ""}
                      </td>
                      <td>{s.documents}/3 documents</td>
                      <td>
                        <span
                          className={`badge ${s.status === "approved" ? "success" : "danger"}`}
                        >
                          {s.status}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`badge ${s.approval_status === "approved" ? "success" : "warning"}`}
                        >
                          {s.approval_status}
                        </span>
                      </td>
                      <td>
                        <Link
                          href={`/shipments/${s.id}`}
                          style={{ fontWeight: 500 }}
                        >
                          Open Review Workspace →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </article>
          </>
        )}

        {activeTab === "accuracy" && report && (
          <div style={{ display: "grid", gap: 24 }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: 16,
              }}
            >
              <div className="card" style={{ padding: 18 }}>
                <p style={{ margin: 0, fontSize: 13, color: "#64748b" }}>
                  Overall Accuracy
                </p>
                <strong style={{ fontSize: 26, color: "#16a34a" }}>
                  {report.overall_accuracy_percent}%
                </strong>
              </div>
              <div className="card" style={{ padding: 18 }}>
                <p style={{ margin: 0, fontSize: 13, color: "#64748b" }}>
                  Total Fields Processed
                </p>
                <strong style={{ fontSize: 26 }}>
                  {report.total_fields_extracted}
                </strong>
              </div>
              <div className="card" style={{ padding: 18 }}>
                <p style={{ margin: 0, fontSize: 13, color: "#64748b" }}>
                  Manual Corrections
                </p>
                <strong style={{ fontSize: 26, color: "#d97706" }}>
                  {report.total_corrections}
                </strong>
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 20,
              }}
            >
              {/* Field-Level Accuracy */}
              <div className="card" style={{ padding: 20 }}>
                <h3 style={{ margin: "0 0 14px", fontSize: 16 }}>
                  Accuracy Per Field
                </h3>
                <table style={{ fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>Total</th>
                      <th>Corrected</th>
                      <th>Accuracy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.by_field.map((f) => (
                      <tr key={f.field}>
                        <td>
                          <b>{f.field.replaceAll("_", " ")}</b>
                        </td>
                        <td>{f.total_extracted}</td>
                        <td>{f.corrected}</td>
                        <td>
                          <span
                            className={`badge ${f.accuracy_percent >= 95 ? "success" : "danger"}`}
                          >
                            {f.accuracy_percent}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Supplier-Level Accuracy */}
              <div className="card" style={{ padding: 20 }}>
                <h3 style={{ margin: "0 0 14px", fontSize: 16 }}>
                  Accuracy Per Supplier
                </h3>
                <table style={{ fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th>Supplier</th>
                      <th>Shipments</th>
                      <th>Fields</th>
                      <th>Accuracy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.by_supplier.map((s) => (
                      <tr key={s.supplier}>
                        <td>
                          <b>{s.supplier}</b>
                        </td>
                        <td>{s.shipments}</td>
                        <td>{s.total_fields}</td>
                        <td>
                          <span
                            className={`badge ${s.accuracy_percent >= 95 ? "success" : "danger"}`}
                          >
                            {s.accuracy_percent}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Recent Audit Log */}
            <div className="card" style={{ padding: 20 }}>
              <h3 style={{ margin: "0 0 14px", fontSize: 16 }}>
                Recent Correction Audit Trail
              </h3>
              {report.recent_audit.length === 0 ? (
                <p className="muted" style={{ fontSize: 13 }}>
                  No manual corrections recorded yet.
                </p>
              ) : (
                <table style={{ fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th>Old Value</th>
                      <th>New Value</th>
                      <th>Reason</th>
                      <th>Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.recent_audit.map((a) => (
                      <tr key={a.id}>
                        <td>
                          <code style={{ color: "#ef4444" }}>
                            {a.old_value || "None"}
                          </code>
                        </td>
                        <td>
                          <code style={{ color: "#16a34a" }}>
                            {a.new_value}
                          </code>
                        </td>
                        <td>{a.reason || "User corrected"}</td>
                        <td style={{ color: "#64748b" }}>
                          {new Date(a.timestamp).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
