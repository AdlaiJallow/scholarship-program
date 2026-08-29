"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError, exportDownloadUrl } from "@/lib/api";
import { ApplicationListItem, Paginated } from "@/lib/types";
import { StatusPill } from "@/components/StatusPill";
import { Icon } from "@/components/Icon";
import { Alert } from "@/components/Alert";
import { EmptyState } from "@/components/EmptyState";
import { Skeleton } from "@/components/Skeleton";

export default function QueuePage() {
  const [applications, setApplications] = useState<ApplicationListItem[] | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams();
    if (statusFilter) params.set("status", statusFilter);
    if (search) params.set("search", search);

    api
      .get<Paginated<ApplicationListItem>>(`/admin/applications?${params.toString()}`)
      .then((data) => setApplications(data.results))
      .catch((err) =>
        setError(err instanceof ApiError && err.status === 403 ? "You do not have access to the Ministry queue." : "Could not load the queue.")
      );
  }, [statusFilter, search]);

  return (
    <div>
      <div className="split" style={{ marginBottom: "var(--space-5)" }}>
        <div>
          <span className="eyebrow">Ministry review</span>
          <h1 style={{ margin: "0.2rem 0 0" }}>Verification queue</h1>
        </div>
        <a className="btn btn-secondary" href={exportDownloadUrl({ export_format: "xlsx" })}>
          <Icon name="download" size={15} />
          Export Excel
        </a>
      </div>

      <div className="row" style={{ marginBottom: "var(--space-4)" }}>
        <div style={{ position: "relative", flex: "1 1 260px" }}>
          <span style={{ position: "absolute", left: "0.7rem", top: "50%", transform: "translateY(-50%)", color: "var(--ink-500)", pointerEvents: "none" }}>
            <Icon name="search" size={15} />
          </span>
          <input
            type="search"
            placeholder="Search name, scholarship ID, reference…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: "2.1rem", width: "100%" }}
          />
        </div>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="under_review">Under Review</option>
          <option value="additional_info_required">Additional Information Required</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      {!applications && !error && (
        <div className="table-scroll" style={{ padding: "var(--space-5)" }}>
          <Skeleton height="1.6rem" width="100%" style={{ marginBottom: "0.75rem" }} />
          <Skeleton height="1.6rem" width="100%" style={{ marginBottom: "0.75rem" }} />
          <Skeleton height="1.6rem" width="100%" />
        </div>
      )}

      {applications && applications.length === 0 && (
        <div className="table-scroll">
          <EmptyState icon="inbox" title="No applications match these filters" description="Try a different search term or clear the status filter." />
        </div>
      )}

      {applications && applications.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Reference</th>
                <th>Student</th>
                <th>Institution</th>
                <th>Status</th>
                <th>Officer</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {applications.map((app) => (
                <tr key={app.id}>
                  <td>
                    <Link href={`/admin/applications/${app.id}`} className="mono" style={{ fontWeight: 600 }}>
                      {app.reference_number || "(draft)"}
                    </Link>
                  </td>
                  <td>{app.student_name}</td>
                  <td>{app.institution}</td>
                  <td>
                    <StatusPill status={app.status} />
                  </td>
                  <td>{app.assigned_officer_name ?? <span className="muted">Unassigned</span>}</td>
                  <td className="muted">{new Date(app.updated_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
