import logging
from datetime import datetime
from typing import Dict, Any, List

from utils.helpers import deep_merge, count_links, _beautify_name
from . import generator

logger = logging.getLogger(__name__)

class ReportAggregator:
    """
    این کلاس مسئولیت تجمیع داده‌های خام، انجام محاسبات آماری و
    فراخوانی ژنراتورها برای تولید گزارش‌های نهایی را بر عهده دارد.
    """
    def _get_top_contributors(self, data: Dict) -> List[Dict]:
        repo_counts = [{"repo": key, "count": count_links(value)} for key, value in data.items()]
        return sorted(repo_counts, key=lambda x: x["count"], reverse=True)[:3]

    def _get_category_distribution(self, data: Dict) -> Dict:
        distribution = {}
        for repo_data in data.values():
            for category, cat_data in repo_data.items():
                distribution[category] = distribution.get(category, 0) + count_links(cat_data)
        return dict(sorted(distribution.items(), key=lambda item: item[1], reverse=True))

    def _generate_chart_data(self, distribution: Dict) -> Dict:
        labels = list(distribution.keys())[:15] # نمایش ۱۵ دسته‌بندی برتر
        values = list(distribution.values())[:15]
        colors = [f"rgba({(i*35+40)%255}, {(i*65+80)%255}, {(i*50+120)%255}, 0.8)" for i, _ in enumerate(labels)]
        borders = [c.replace("0.8", "1") for c in colors]
        return {"labels": labels, "values": values, "colors": colors, "borders": borders}

    def process_and_generate_reports(
        self,
        regex_items: List[Dict],
        ai_items: List[Dict],
        scan_stats: List[Dict],
        total_files: int,
        execution_time: float
    ):
        final_data = {}

        for item in regex_items:
            repo_key = item["repo_key"]
            if repo_key not in final_data:
                final_data[repo_key] = {}
            deep_merge(item["data"], final_data[repo_key])

        ai_success_count_by_repo = {}
        for item in ai_items:
            repo_key = item.get("repo_key")
            if not repo_key: continue
            
            category = _beautify_name(item.get("category", "AI Uncategorized"))
            if category == "Ai Failed - Uncategorized":
                continue # موارد ناموفق را در شمارش موفقیت لحاظ نکن

            ai_success_count_by_repo[repo_key] = ai_success_count_by_repo.get(repo_key, 0) + 1
            sub_category = _beautify_name(item.get("sub_category", "General"))
            name = _beautify_name(item.get("name", "Unnamed Link"))
            link = item.get("link")

            if not all([repo_key, category, sub_category, name, link]):
                logger.warning(f"Skipping incomplete AI item: {item}")
                continue

            if repo_key not in final_data:
                final_data[repo_key] = {}
            
            current_level = final_data[repo_key].setdefault(category, {}).setdefault(sub_category, {})
            current_level[name] = link

        if not final_data:
            logger.warning("No usable config links found to generate output files.")
            return

        # --- FIX: تکمیل چرخه داده برای گزارش‌دهی ---
        final_repo_stats = []
        total_ai_items = 0
        total_ai_success = 0
        for stat in scan_stats:
            repo_name = stat["repo"]
            repo_key = _beautify_name(repo_name.split('/')[-1])
            links_found = count_links(final_data.get(repo_key, {}))
            
            ai_total = stat.get('ai_total_items', 0)
            ai_success = ai_success_count_by_repo.get(repo_key, 0)
            total_ai_items += ai_total
            total_ai_success += ai_success

            final_repo_stats.append({
                "repo": repo_name,
                "status": stat["status"],
                "links_found": links_found,
                "time": stat["time"],
                "files_analyzed": stat.get('files_analyzed', 0),
                "regex_success_count": stat.get('regex_success_count', 0),
                "ai_success_count": ai_success,
                "ai_total_items": ai_total,
                "ai_success_rate": (ai_success / ai_total * 100) if ai_total > 0 else 0
            })

        total_links_found = count_links(final_data)
        run_stats = {
            "run_timestamp": datetime.now().isoformat(),
            "repos_scanned": len(scan_stats),
            "total_files_analyzed": total_files,
            "total_unique_links": total_links_found,
            "repo_stats": final_repo_stats,
            "execution_time": execution_time,
            "links_per_file": total_links_found / total_files if total_files > 0 else 0,
            "ai_success_rate": (total_ai_success / total_ai_items * 100) if total_ai_items > 0 else 0
        }

        top_contributors = self._get_top_contributors(final_data)
        category_dist = self._get_category_distribution(final_data)
        chart_data = self._generate_chart_data(category_dist)

        generator.generate_js_file(final_data)
        text_report = generator.generate_text_report(run_stats)
        generator.generate_html_dashboard(run_stats, top_contributors, chart_data)
        
        logger.info("\n" + text_report)
