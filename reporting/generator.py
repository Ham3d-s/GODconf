import json
import logging
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)
LOG_DIR = "reports"

def generate_js_file(data: Dict[str, Any]):
    """فایل داده JavaScript را برای داشبورد وب تولید می‌کند."""
    js_filename = os.path.join(LOG_DIR, 'public-configs-data.js')
    js_object_string = json.dumps(data, indent=4, ensure_ascii=False)
    final_js_code = f"export const INITIAL_PUBLIC_CONFIGS = {js_object_string};\n"
    with open(js_filename, "w", encoding="utf-8") as f:
        f.write(final_js_code)
    logger.info(f"Generated JavaScript data file: {js_filename}")

def generate_text_report(stats: Dict[str, Any]) -> str:
    """یک گزارش متنی ساده از خلاصه اجرا تولید می‌کند."""
    report_lines = [
        f"--- GODconf v1.0 Report ---",
        f"Generated on: {stats['run_timestamp']}",
        "="*40,
        "\n**Overall Summary:**",
        f"  - Repositories Scanned: {stats['repos_scanned']}",
        f"  - Total Files Analyzed: {stats['total_files_analyzed']}",
        f"  - Total Unique Links Found: {stats['total_unique_links']}",
        f"  - Links per File Ratio: {stats.get('links_per_file', 0):.2f}",
        f"  - AI Success Rate: {stats.get('ai_success_rate', 0):.2f}%",
        f"  - Total Execution Time: {stats['execution_time']:.2f} seconds",
        "\n**Repository Breakdown:**"
    ]
    for repo_stat in sorted(stats.get('repo_stats', []), key=lambda x: x['links_found'], reverse=True):
        report_lines.extend([
            f"  - {repo_stat['repo']}:",
            f"    - Status: {repo_stat['status']}",
            f"    - Files Analyzed: {repo_stat['files_analyzed']}",
            f"    - Links Found: {repo_stat['links_found']}",
            f"    - Scan Time: {repo_stat['time']:.2f}s",
            f"    - AI Success: {repo_stat.get('ai_success_count', 0)}/{repo_stat.get('ai_total_items', 0)} ({repo_stat.get('ai_success_rate', 0):.1f}%)"
        ])
    report_lines.append("\n" + "="*40 + "\nReport generated successfully.")
    
    report_str = "\n".join(report_lines)
    with open(os.path.join(LOG_DIR, "Execution_Report.log"), "w", encoding="utf-8") as f:
        f.write(report_str)
    logger.info("Generated text report.")
    return report_str

def generate_html_dashboard(stats: Dict[str, Any], top_repos: List, chart_data: Dict):
    """
    --- RE-ARCHITECTED: داشبورد HTML کاملاً جدید و هوشمند ---
    داشبورد گزارش تصویری HTML را با جزئیات و معیارهای کلیدی عملکرد (KPIs) تولید می‌کند.
    """
    repo_rows_html = ""
    total_links = stats.get('total_unique_links', 1)
    for s in sorted(stats.get('repo_stats', []), key=lambda x: x['links_found'], reverse=True):
        percentage = (s['links_found'] / total_links * 100)
        repo_rows_html += f"""
        <tr>
            <td><a href="https://github.com/{s['repo']}" target="_blank">{s['repo']}</a></td>
            <td><span class="status status-{s['status'].lower()}">{s['status']}</span></td>
            <td>{s['files_analyzed']}</td>
            <td>{s['links_found']}</td>
            <td>{s['time']:.2f}s</td>
            <td class="progress-cell">
                <div class="progress-bar-container"><div class="progress-bar" style="width: {percentage:.2f}%;"></div></div>
                <span>{percentage:.2f}%</span>
            </td>
            <td>
                <span class="pill pill-regex">{s.get('regex_success_count', 0)}</span> / 
                <span class="pill pill-ai">{s.get('ai_success_count', 0)}</span>
            </td>
        </tr>
        """
    
    top_contributors_html = ""
    medals = ["🥇", "🥈", "🥉"]
    for i, repo in enumerate(top_repos):
        top_contributors_html += f"<li>{medals[i]} <strong>{repo['repo']}</strong> ({repo['count']} links)</li>"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GODconf v1.0 - Executive Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Roboto', sans-serif; background-color: #f4f7f6; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 1400px; margin: auto; }}
            .header {{ background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; padding: 25px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 8px 16px rgba(0,0,0,0.1); text-align: center; }}
            .header h1 {{ margin: 0; font-size: 2.5em; }} .header p {{ margin: 5px 0 0; opacity: 0.9; }}
            .card {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 25px; }}
            h2 {{ font-size: 1.6em; margin-top: 0; padding-bottom: 15px; border-bottom: 3px solid #e9ecef; color: #1e3c72; }}
            .grid-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; }}
            .stat-card {{ text-align: center; background-color: #ffffff; padding: 20px; border-radius: 8px; border-bottom: 4px solid #2a5298; transition: transform 0.2s, box-shadow 0.2s; }}
            .stat-card:hover {{ transform: translateY(-5px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); }}
            .stat-card .value {{ font-size: 2.4em; font-weight: 700; color: #1e3c72; }} .stat-card .label {{ font-size: 1.1em; color: #555; margin-top: 8px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.95em; }} th, td {{ padding: 15px; border-bottom: 1px solid #dee2e6; text-align: left; vertical-align: middle; }}
            th {{ background-color: #e9ecef; color: #495057; text-transform: uppercase; font-size: 0.85em; }}
            tr:hover {{ background-color: #f8f9fa; }}
            .status {{ padding: 6px 12px; border-radius: 15px; color: white; font-weight: bold; font-size: 0.9em; text-align: center; }}
            .status-success {{ background-color: #28a745; }} .status-failed {{ background-color: #dc3545; }}
            .progress-cell {{ display: flex; align-ins: center; gap: 10px; }}
            .progress-bar-container {{ width: 120px; height: 12px; background-color: #e9ecef; border-radius: 6px; overflow: hidden; }}
            .progress-bar {{ height: 100%; background: linear-gradient(90deg, #1e3c72, #2a5298); border-radius: 6px; }}
            .chart-container {{ position: relative; height: 450px; }}
            .top-contributors ul {{ list-style: none; padding-left: 0; }} .top-contributors li {{ font-size: 1.1em; padding: 10px 0; border-bottom: 1px solid #f1f1f1; }}
            .top-contributors li:last-child {{ border-bottom: none; }}
            .pill {{ padding: 4px 10px; border-radius: 12px; font-size: 0.85em; font-weight: bold; color: white; }}
            .pill-regex {{ background-color: #17a2b8; }} .pill-ai {{ background-color: #fd7e14; }}
            a {{ color: #1e3c72; text-decoration: none; }} a:hover {{ text-decoration: underline; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 0.9em; color: #888; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h1>GODconf</h1><p>Executive Dashboard & Performance Analysis</p><p>Generated on: {stats['run_timestamp']}</p></div>
            <div class="card"><h2>Key Performance Indicators (KPIs)</h2><div class="grid-container">
                <div class="stat-card"><div class="value">{stats['total_unique_links']}</div><div class="label">Total Links Found</div></div>
                <div class="stat-card"><div class="value">{stats['repos_scanned']}</div><div class="label">Repositories Scanned</div></div>
                <div class="stat-card"><div class="value">{stats['total_files_analyzed']}</div><div class="label">Files Analyzed</div></div>
                <div class="stat-card"><div class="value">{stats['links_per_file']:.2f}</div><div class="label">Links / File</div></div>
                <div class="stat-card"><div class="value">{stats['ai_success_rate']:.1f}%</div><div class="label">AI Success Rate</div></div>
                <div class="stat-card"><div class="value">{stats['execution_time']:.2f}s</div><div class="label">Total Execution Time</div></div>
            </div></div>
            <div class="grid-container" style="grid-template-columns: 2fr 1fr;">
                <div class="card"><h2>Category Distribution</h2><div class="chart-container"><canvas id="categoryChart"></canvas></div></div>
                <div class="card top-contributors"><h2>Top Contributors</h2><ul>{top_contributors_html}</ul></div>
            </div>
            <div class="card"><h2>Repository Deep Dive</h2><table><thead><tr><th>Repository</th><th>Status</th><th>Files</th><th>Links</th><th>Time</th><th>Contribution</th><th>Categorization (Regex/AI)</th></tr></thead><tbody>{repo_rows_html}</tbody></table></div>
            <div class="footer">GODconf v1.0 (Resilient Architecture)</div>
        </div>
        <script>
            const ctx = document.getElementById('categoryChart').getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{ 
                    labels: {json.dumps(chart_data['labels'])}, 
                    datasets: [{{ 
                        label: 'Links Found', 
                        data: {json.dumps(chart_data['values'])}, 
                        backgroundColor: {json.dumps(chart_data['colors'])}, 
                        borderColor: {json.dumps(chart_data['borders'])},
                        borderWidth: 1 
                    }}] 
                }},
                options: {{ 
                    indexAxis: 'y',
                    responsive: true, 
                    maintainAspectRatio: false, 
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{ x: {{ beginAtZero: true }} }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    with open(os.path.join(LOG_DIR, "Visual_Report.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info("Generated HTML dashboard.")