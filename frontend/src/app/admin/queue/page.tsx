"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError, exportDownloadUrl } from "@/lib/api";
import { ApplicationListItem, Paginated } from "@/lib/types";
import { StatusPill } from "@/components/StatusPill";

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
    <div className="stack">
      <h1>Ministry verification queue</h1>

      <div className="row">
        <input placeholder="Search name, scholarship ID, reference…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="under_review">Under Review</option>
          <option value="additional_info_required">Additional Information Required</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
        <a className="btn btn-secondary" href={exportDownloadUrl({ export_format: "xlsx" })}>
          Export Excel
        </a>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {applications && (
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
                    <Link href={`/admin/applications/${app.id}`}>{app.reference_number || "(draft)"}</Link>
                  </td>
                  <td>{app.student_name}</td>
                  <td>{app.institution}</td>
                  <td>
                    <StatusPill status={app.status} />
                  </td>
                  <td>{app.assigned_officer_name ?? <span className="muted">Unassigned</span>}</td>
                  <td>{new Date(app.updated_at).toLocaleDateString()}</td>
                </tr>
              ))}
              {applications.length === 0 && (
                <tr>
                  <td colSpan={6} className="muted">
                    No applications match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
