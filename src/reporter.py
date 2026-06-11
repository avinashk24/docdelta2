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
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; 
             padding-bottom: 10px; }
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

        /* Risk items */
        .risk-item { background: white; border-radius: 8px;
                     margin: 14px 0; overflow: hidden;
                     box-shadow: 0 1px 4px rgba(0,0,0,0.08);
                     border-left: 5px solid #ccc; }
        .risk-critical { border-color: #c0392b; }
        .risk-high     { border-color: #e67e22; }
        .risk-medium   { border-color: #f1c40f; }
        .risk-low      { border-color: #27ae60; }

        .risk-header { padding: 14px 18px 8px; }
        .risk-body   { padding: 0 18px 14px; }

        /* Actual changed content box */
        .changed-content { margin: 10px 0;
                           border-radius: 6px; overflow: hidden; }
        .changed-content .label {
            font-size: 0.72em; font-weight: bold;
            text-transform: uppercase; letter-spacing: 0.5px;
            padding: 4px 10px; color: white; }
        .changed-content .text {
            padding: 10px 14px; font-size: 0.88em;
            line-height: 1.65; font-family: Georgia, serif;
            white-space: pre-wrap; word-break: break-word; }

        /* Color variants per change type */
        .content-addition .label  { background: #27ae60; }
        .content-addition .text   { background: #eafaf1;
                                    border: 1px solid #a9dfbf; }
        .content-deletion .label  { background: #e74c3c; }
        .content-deletion .text   { background: #fdecea;
                                    border: 1px solid #f5b7b1; }
        .content-update-old .label { background: #7f8c8d; }
        .content-update-old .text  { background: #f2f3f4;
                                     border: 1px solid #d5d8dc;
                                     text-decoration: line-through;
                                     color: #7f8c8d; }
        .content-update-new .label { background: #e67e22; }
        .content-update-new .text  { background: #fef9e7;
                                     border: 1px solid #f9e79f; }

        /* Risk reason / recommendation */
        .risk-analysis { margin-top: 10px; padding: 10px 14px;
                         background: #f8f9fa; border-radius: 6px;
                         font-size: 0.88em; line-height: 1.6; }
        .risk-analysis p { margin: 4px 0; }

        /* Badges */
        .badge { display: inline-block; padding: 2px 10px;
                 border-radius: 12px; font-size: 0.75em;
                 font-weight: bold; text-transform: uppercase;
                 margin-right: 6px; }
        .badge-critical { background: #fdecea; color: #c0392b; }
        .badge-high     { background: #fef0e6; color: #e67e22; }
        .badge-medium   { background: #fefde6; color: #b7950b; }
        .badge-low      { background: #eafaf1; color: #27ae60; }
        .badge-type     { background: #eaf0fb; color: #2980b9; }
        .badge-llm      { background: #f4ecf7; color: #8e44ad;
                          font-size: 0.68em; }

        .section-path { font-size: 0.78em; color: #7f8c8d;
                        margin-top: 4px; font-family: monospace; }
        .section-header { font-size: 1em; font-weight: bold;
                          color: #2c3e50; }

        /* Change sections */
        .change { background: white; border-radius: 8px;
                  padding: 16px 20px; margin: 12px 0;
                  box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
        .diff-box { margin-top: 8px; padding: 10px 14px;
                    border-radius: 6px; font-size: 0.88em;
                    line-height: 1.6; white-space: pre-wrap; }
        .old      { background: #fdecea; border-left: 4px solid #e74c3c; }
        .new      { background: #eafaf1; border-left: 4px solid #27ae60; }
        .semantic { background: #fef9e7; border-left: 4px solid #f1c40f;
                    margin-top: 8px; font-style: italic; }
        .section-tag { font-size: 0.75em; font-weight: bold;
                       background: #eaf0fb; color: #2980b9;
                       padding: 2px 10px; border-radius: 12px;
                       display: inline-block; margin-bottom: 8px; }
        .meta { color: #888; font-size: 0.82em; margin-bottom: 24px; }

        /* Collapsible */
        details summary { cursor: pointer; user-select: none;
                          color: #2980b9; font-size: 0.85em;
                          margin-top: 6px; }
        details summary:hover { text-decoration: underline; }
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

<!-- ═══════════════════════════════════════════════════ -->
<!--  RISK ASSESSMENT                                    -->
<!-- ═══════════════════════════════════════════════════ -->
{% if risks %}
<h2>⚠️ Risk Assessment</h2>
{% for risk in risks %}
<div class="risk-item risk-{{ risk.risk_level }}">

    <!-- Header row: badges + section path -->
    <div class="risk-header">
        <span class="badge badge-{{ risk.risk_level }}">
            {{ risk.risk_level }}</span>
        <span class="badge badge-type">
            {{ risk.change_type }}</span>
        {% if risk.llm_analyzed %}
        <span class="badge badge-llm">🤖 LLM analysed</span>
        {% endif %}
        <div class="section-header">{{ risk.section }}</div>
    </div>

    <div class="risk-body">

        <!-- ── Actual changed content ── -->
        {% if risk.change_type == 'addition' and risk.new_content %}
        <div class="changed-content content-addition">
            <div class="label">➕ Added Text</div>
            <div class="text">{{ risk.new_content }}</div>
        </div>

        {% elif risk.change_type == 'deletion' and risk.old_content %}
        <div class="changed-content content-deletion">
            <div class="label">❌ Deleted Text</div>
            <div class="text">{{ risk.old_content }}</div>
        </div>

        {% elif risk.change_type == 'update' %}
            {% if risk.old_content %}
            <div class="changed-content content-update-old">
                <div class="label">📄 Old Version</div>
                <div class="text">{{ risk.old_content }}</div>
            </div>
            {% endif %}
            {% if risk.new_content %}
            <div class="changed-content content-update-new">
                <div class="label">✏️ New Version</div>
                <div class="text">{{ risk.new_content }}</div>
            </div>
            {% endif %}
        {% endif %}

        <!-- ── Risk reason + recommendation ── -->
        <div class="risk-analysis">
            <p>🔍 <strong>Reason:</strong> {{ risk.risk_reason }}</p>
            <p>💡 <strong>Recommendation:</strong>
               {{ risk.recommendation }}</p>
        </div>

    </div>
</div>
{% endfor %}
{% endif %}

<!-- ═══════════════════════════════════════════════════ -->
<!--  ADDITIONS                                          -->
<!-- ═══════════════════════════════════════════════════ -->
{% if changes.additions %}
<h2>➕ Additions ({{ changes.additions|length }})</h2>
{% for item in changes.additions %}
<div class="change">
    <span class="section-tag">{{ item.section }}</span>
    <div class="diff-box new">{{ item.content }}</div>
</div>
{% endfor %}
{% endif %}

<!-- ═══════════════════════════════════════════════════ -->
<!--  UPDATES                                            -->
<!-- ═══════════════════════════════════════════════════ -->
{% if changes.updates %}
<h2>✏️ Updates ({{ changes.updates|length }})</h2>
{% for item in changes.updates %}
<div class="change">
    <span class="section-tag">{{ item.section }}</span>
    <div class="diff-box old"><strong>Old:</strong> {{ item.old_content }}</div>
    <div class="diff-box new"><strong>New:</strong> {{ item.new_content }}</div>
    {% if item.semantic_diff %}
    <div class="diff-box semantic">
        💬 <strong>What changed:</strong> {{ item.semantic_diff }}
    </div>
    {% endif %}
</div>
{% endfor %}
{% endif %}

<!-- ═══════════════════════════════════════════════════ -->
<!--  DELETIONS                                          -->
<!-- ═══════════════════════════════════════════════════ -->
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

        with open(output_path, "w", encoding="utf-8") as f:
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
    ### {{ risk.risk_level | upper }} — {{ risk.change_type }} {% if risk.llm_analyzed %} - LLM ANALYZED {% endif %}}

    - **Section:** {{ risk.section }}
    {% if risk.change_type == 'addition' and risk.new_content %}
    **➕ Added Text**
    > {{ risk.new_content }}

    {% elif risk.change_type == 'deletion' and risk.old_content %}
    **❌ Deleted Text**
    > {{ risk.old_content }}

    {% elif risk.change_type == 'update' %}
        {% if risk.old_content %}
    **📄 Old Version**
    > {{ risk.old_content }}
        {% endif %}
        {% if risk.new_content %}

    **✏️ New Version**
    > {{ risk.new_content }}
        {% endif %}
    {% endif %}
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