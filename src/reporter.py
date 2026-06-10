from jinja2 import Template
from datetime import datetime

class Reporter:
    def generate(self, report: dict, output_path: str,
                 doc1_name: str, doc2_name: str, fmt: str = "html"):
        if fmt == "md":
            self.generate_markdown(report, output_path, doc1_name, doc2_name)
        elif fmt == "html":
            self.generate_html(report, output_path, doc1_name, doc2_name)
        else:
            raise ValueError(f"Unsupported format: {fmt!r}. Use 'html' or 'md'.")

    def generate_html(self, report: dict, output_path: str,
                      doc1_name: str, doc2_name: str):

        template = Template("""
<!DOCTYPE html>
<html>
<head>
    <title>DocDelta Report</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1100px; 
               margin: 40px auto; background: #f5f5f5; color: #333; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #2c3e50; margin-top: 30px; }

        /* Summary Cards */
        .summary { display: flex; gap: 16px; margin: 24px 0; flex-wrap: wrap; }
        .card { background: white; border-radius: 10px; padding: 20px 28px;
                flex: 1; min-width: 130px; text-align: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .card .number { font-size: 2.2em; font-weight: bold; }
        .card .label  { font-size: 0.85em; color: #777; margin-top: 4px; }
        .add  .number { color: #27ae60; }
        .upd  .number { color: #e67e22; }
        .del  .number { color: #e74c3c; }
        .risk .number { color: #8e44ad; }

        /* Change items */
        .change { background: white; border-radius: 8px; padding: 16px 20px;
                  margin: 12px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
        .change .section-tag { font-size: 0.78em; font-weight: bold;
                               background: #eaf0fb; color: #2980b9;
                               padding: 2px 10px; border-radius: 12px;
                               display: inline-block; margin-bottom: 8px; }
        .change .content { font-size: 0.92em; line-height: 1.6; color: #555; }
        .diff-box { margin-top: 10px; padding: 10px 14px; border-radius: 6px;
                    font-size: 0.88em; line-height: 1.6; }
        .old { background: #fdecea; border-left: 4px solid #e74c3c; }
        .new { background: #eafaf1; border-left: 4px solid #27ae60; }
        .semantic { background: #fef9e7; border-left: 4px solid #f1c40f;
                    margin-top: 8px; font-style: italic; }

        /* Risk items */
        .risk-item { background: white; border-radius: 8px; padding: 16px 20px;
                     margin: 12px 0; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
                     border-left: 5px solid #ccc; }
        .risk-critical { border-color: #c0392b; }
        .risk-high     { border-color: #e67e22; }
        .risk-medium   { border-color: #f1c40f; }
        .risk-low      { border-color: #27ae60; }

        .badge { display: inline-block; padding: 2px 10px; border-radius: 12px;
                 font-size: 0.78em; font-weight: bold; text-transform: uppercase; 
                 margin-bottom: 6px; }
        .badge-critical { background: #fdecea; color: #c0392b; }
        .badge-high     { background: #fef0e6; color: #e67e22; }
        .badge-medium   { background: #fefde6; color: #b7950b; }
        .badge-low      { background: #eafaf1; color: #27ae60; }

        .meta { color: #888; font-size: 0.82em; margin-bottom: 24px; }
        .section-header { font-size: 1.1em; font-weight: bold; 
                          color: #2c3e50; margin-bottom: 6px; }
    </style>
</head>
<body>

<h1>📄 DocDelta — Policy Comparison Report</h1>
<div class="meta">
    <strong>Document 1:</strong> {{ doc1 }} &nbsp;|&nbsp;
    <strong>Document 2:</strong> {{ doc2 }} &nbsp;|&nbsp;
    <strong>Generated:</strong> {{ timestamp }}
</div>

<!-- Summary Cards -->
<div class="summary">
    <div class="card add">
        <div class="number">{{ summary.additions }}</div>
        <div class="label">➕ Additions</div>
    </div>
    <div class="card upd">
        <div class="number">{{ summary.updates }}</div>
        <div class="label">✏️ Updates</div>
    </div>
    <div class="card del">
        <div class="number">{{ summary.deletions }}</div>
        <div class="label">❌ Deletions</div>
    </div>
    <div class="card risk">
        <div class="number">{{ summary.critical_risks }}</div>
        <div class="label">🔴 Critical Risks</div>
    </div>
    <div class="card risk">
        <div class="number">{{ summary.high_risks }}</div>
        <div class="label">🟠 High Risks</div>
    </div>
</div>

<!-- Risks -->
{% if risks %}
<h2>⚠️ Risk Assessment</h2>
{% for risk in risks %}
<div class="risk-item risk-{{ risk.risk_level }}">
    <span class="badge badge-{{ risk.risk_level }}">{{ risk.risk_level }}</span>
    <span class="badge" style="background:#eaf0fb;color:#2980b9">
        {{ risk.change_type }}</span>
    <div class="section-header">{{ risk.section }}</div>
    <div class="content">🔍 <strong>Reason:</strong> {{ risk.risk_reason }}</div>
    <div class="content">💡 <strong>Recommendation:</strong> {{ risk.recommendation }}</div>
</div>
{% endfor %}
{% endif %}

<!-- Additions -->
{% if changes.additions %}
<h2>➕ Additions ({{ changes.additions|length }})</h2>
{% for item in changes.additions %}
<div class="change">
    <span class="section-tag">{{ item.section }}</span>
    <div class="diff-box new">{{ item.content }}</div>
</div>
{% endfor %}
{% endif %}

<!-- Updates -->
{% if changes.updates %}
<h2>✏️ Updates ({{ changes.updates|length }})</h2>
{% for item in changes.updates %}
<div class="change">
    <span class="section-tag">{{ item.section }}</span>
    <div class="diff-box old"><strong>Old:</strong> {{ item.old_content }}</div>
    <div class="diff-box new"><strong>New:</strong> {{ item.new_content }}</div>
    <div class="diff-box semantic">
        💬 <strong>What changed:</strong> {{ item.semantic_diff }}
    </div>
</div>
{% endfor %}
{% endif %}

<!-- Deletions -->
{% if changes.deletions %}
<h2>❌ Deletions ({{ changes.deletions|length }})</h2>
{% for item in changes.deletions %}
<div class="change">
    <span class="section-tag">{{ item.section }}</span>
    <div class="diff-box old">{{ item.content }}</div>
</div>
{% endfor %}
{% endif %}

</body>
</html>
        """)

        html = template.render(
            doc1=doc1_name,
            doc2=doc2_name,
            timestamp=datetime.now().strftime("%d %b %Y, %I:%M %p"),
            summary=report["summary"],
            changes=report["changes"],
            risks=report["risks"]
        )

        with open(output_path, "w") as f:
            f.write(html)

        print(f"📊 HTML report saved → {output_path}")

    def generate_markdown(self, report: dict, output_path: str,
                          doc1_name: str, doc2_name: str):
        template = Template("""# DocDelta — Policy Comparison Report

**Document 1:** {{ doc1 }} | **Document 2:** {{ doc2 }} | **Generated:** {{ timestamp }}

## Summary

| Metric | Count |
|--------|------:|
| Additions | {{ summary.additions }} |
| Updates | {{ summary.updates }} |
| Deletions | {{ summary.deletions }} |
| Critical Risks | {{ summary.critical_risks }} |
| High Risks | {{ summary.high_risks }} |

{% if risks %}
## Risk Assessment

{% for risk in risks %}
### {{ risk.section }} — {{ risk.risk_level | upper }}

- **Change type:** {{ risk.change_type }}
- **Reason:** {{ risk.risk_reason }}
- **Recommendation:** {{ risk.recommendation }}

{% endfor %}
{% endif %}
{% if changes.additions %}
## Additions ({{ changes.additions|length }})

{% for item in changes.additions %}
### {{ item.section }}

> {{ item.content }}

{% endfor %}
{% endif %}
{% if changes.updates %}
## Updates ({{ changes.updates|length }})

{% for item in changes.updates %}
### {{ item.section }}

**Old:**
> {{ item.old_content }}

**New:**
> {{ item.new_content }}

**What changed:** {{ item.semantic_diff }}

{% endfor %}
{% endif %}
{% if changes.deletions %}
## Deletions ({{ changes.deletions|length }})

{% for item in changes.deletions %}
### {{ item.section }}

> {{ item.content }}

{% endfor %}
{% endif %}
""")

        md = template.render(
            doc1=doc1_name,
            doc2=doc2_name,
            timestamp=datetime.now().strftime("%d %b %Y, %I:%M %p"),
            summary=report["summary"],
            changes=report["changes"],
            risks=report["risks"]
        )

        with open(output_path, "w") as f:
            f.write(md)

        print(f"📊 Markdown report saved → {output_path}")