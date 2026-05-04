"""Interactive MRZ Guide -- comprehensive education + interactive tools.

Generates a self-contained HTML/CSS/JS page that visually explains
MRZ structure for TD1, TD2, TD3 formats with interactive breakdowns,
a live check digit calculator, worked examples, and reference tables.
"""


def get_mrz_guide_html() -> str:
    """Return complete HTML for the MRZ Guide tab."""
    return _HTML


_HTML = """
<div id="mrz-guide-root">

<style>
#mrz-guide-root {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: #e2e8f0;
  max-width: 900px;
  margin: 0 auto;
  padding: 20px 16px;
  background: #0f172a;
}
#mrz-guide-root * { box-sizing: border-box; }
#mrz-guide-root h2 {
  color: #f8fafc;
  font-size: 22px;
  margin: 40px 0 12px;
  border-bottom: 2px solid #334155;
  padding-bottom: 8px;
}
#mrz-guide-root h3 {
  color: #cbd5e1;
  font-size: 17px;
  margin: 24px 0 8px;
}
#mrz-guide-root h4 {
  color: #94a3b8;
  font-size: 15px;
  margin: 16px 0 6px;
}
#mrz-guide-root p {
  color: #94a3b8;
  line-height: 1.7;
  margin: 8px 0;
  font-size: 14px;
}
#mrz-guide-root strong { color: #e2e8f0; }
#mrz-guide-root code {
  background: #1e293b;
  padding: 1px 5px;
  border-radius: 3px;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 13px;
  color: #fb923c;
}
#mrz-guide-root ul {
  color: #94a3b8;
  line-height: 1.7;
  padding-left: 20px;
  font-size: 14px;
}
#mrz-guide-root li { margin: 4px 0; }

/* Cards */
.mrz-card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 20px;
  margin: 16px 0;
}

/* Format comparison */
.format-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin: 16px 0;
}
.format-item {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 14px;
  text-align: center;
}
.format-item .fmt-name {
  font-weight: 700;
  font-size: 16px;
  color: #60a5fa;
  margin-bottom: 4px;
}
.format-item .fmt-dims {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #34d399;
  margin-bottom: 4px;
}
.format-item .fmt-use {
  font-size: 12px;
  color: #64748b;
}

/* MRZ container */
.mrz-box {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 20px;
  margin: 16px 0;
  position: relative;
  overflow-x: auto;
}
.mrz-box-label {
  font-size: 12px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 8px;
}
.mrz-line {
  font-family: 'Courier New', Consolas, monospace;
  font-size: 14px;
  letter-spacing: 1.5px;
  line-height: 2.2;
  white-space: nowrap;
}

/* Field spans */
.mrz-field {
  padding: 2px 0;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 2px;
}
.mrz-field:hover {
  transform: translateY(-1px);
  filter: brightness(1.3);
}
.mrz-field.active {
  filter: brightness(1.4);
}

/* Field colors */
.mrz-doc-type { color: #60a5fa; border-bottom-color: #3b82f6; }
.mrz-doc-type:hover, .mrz-doc-type.active {
  background: rgba(96,165,250,0.15);
  box-shadow: 0 0 10px rgba(96,165,250,0.3);
}
.mrz-country { color: #34d399; border-bottom-color: #10b981; }
.mrz-country:hover, .mrz-country.active {
  background: rgba(52,211,153,0.15);
  box-shadow: 0 0 10px rgba(52,211,153,0.3);
}
.mrz-name { color: #c084fc; border-bottom-color: #a855f7; }
.mrz-name:hover, .mrz-name.active {
  background: rgba(192,132,252,0.15);
  box-shadow: 0 0 10px rgba(192,132,252,0.3);
}
.mrz-doc-num { color: #fb923c; border-bottom-color: #f97316; }
.mrz-doc-num:hover, .mrz-doc-num.active {
  background: rgba(251,146,60,0.15);
  box-shadow: 0 0 10px rgba(251,146,60,0.3);
}
.mrz-check { color: #f87171; border-bottom-color: #ef4444; }
.mrz-check:hover, .mrz-check.active {
  background: rgba(248,113,113,0.15);
  box-shadow: 0 0 10px rgba(248,113,113,0.3);
}
.mrz-nationality { color: #2dd4bf; border-bottom-color: #14b8a6; }
.mrz-nationality:hover, .mrz-nationality.active {
  background: rgba(45,212,191,0.15);
  box-shadow: 0 0 10px rgba(45,212,191,0.3);
}
.mrz-dob { color: #fbbf24; border-bottom-color: #f59e0b; }
.mrz-dob:hover, .mrz-dob.active {
  background: rgba(251,191,36,0.15);
  box-shadow: 0 0 10px rgba(251,191,36,0.3);
}
.mrz-sex { color: #f472b6; border-bottom-color: #ec4899; }
.mrz-sex:hover, .mrz-sex.active {
  background: rgba(244,114,182,0.15);
  box-shadow: 0 0 10px rgba(244,114,182,0.3);
}
.mrz-expiry { color: #22d3ee; border-bottom-color: #06b6d4; }
.mrz-expiry:hover, .mrz-expiry.active {
  background: rgba(34,211,238,0.15);
  box-shadow: 0 0 10px rgba(34,211,238,0.3);
}
.mrz-personal, .mrz-optional { color: #9ca3af; border-bottom-color: #6b7280; }
.mrz-personal:hover, .mrz-personal.active,
.mrz-optional:hover, .mrz-optional.active {
  background: rgba(156,163,175,0.15);
  box-shadow: 0 0 10px rgba(156,163,175,0.3);
}

/* Info panel */
.mrz-info {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 14px 18px;
  margin-top: 12px;
  min-height: 50px;
  transition: all 0.2s ease;
}
.mrz-info-label {
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 4px;
}
.mrz-info-value {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 4px;
}
.mrz-info-desc {
  font-size: 13px;
  color: #64748b;
}
.mrz-info-hint {
  color: #475569;
  font-size: 13px;
  font-style: italic;
}

/* Legend */
.mrz-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 12px 0;
}
.mrz-legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #94a3b8;
}
.mrz-legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

/* Buttons */
.mrz-btn {
  background: #1e293b;
  color: #94a3b8;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 6px 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 8px;
}
.mrz-btn:hover {
  background: #334155;
  color: #e2e8f0;
}
.mrz-btn-primary {
  background: #f97316;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 20px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.mrz-btn-primary:hover { background: #ea580c; }
.mrz-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

/* Entrance animation */
@keyframes mrz-enter {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
.mrz-animating .mrz-field {
  opacity: 0;
  animation: mrz-enter 0.3s ease forwards;
}

/* Live calculator */
.calc-input {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  color: #fb923c;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 18px;
  letter-spacing: 2px;
  padding: 12px 16px;
  width: 100%;
  outline: none;
  text-transform: uppercase;
}
.calc-input:focus { border-color: #f97316; }
.calc-input::placeholder { color: #334155; letter-spacing: 1px; }

.calc-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  margin: 12px 0;
}
.calc-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 6px;
  border-radius: 4px;
  background: #1e293b;
  min-width: 40px;
  transition: all 0.3s ease;
}
.calc-cell.calc-active {
  background: #334155;
  box-shadow: 0 0 12px rgba(251,191,36,0.4);
}
.calc-cell.calc-done {
  background: #1e3a2f;
}
.calc-cell .cc-char {
  font-family: 'Courier New', monospace;
  font-size: 16px;
  font-weight: 700;
  color: #fb923c;
}
.calc-cell .cc-val { font-size: 10px; color: #94a3b8; }
.calc-cell .cc-wt { font-size: 10px; color: #60a5fa; }
.calc-cell .cc-prod { font-size: 11px; color: #34d399; font-weight: 600; }

.calc-result {
  margin-top: 12px;
  font-size: 16px;
  color: #e2e8f0;
}
.calc-result-num {
  color: #f87171;
  font-weight: 700;
  font-size: 22px;
}

/* Worked examples */
.we-formula {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 12px 16px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #94a3b8;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 8px 0;
}
.we-field { font-weight: 700; }
.we-field-dn { color: #fb923c; }
.we-field-dc { color: #f87171; }
.we-field-dob { color: #fbbf24; }
.we-field-dobc { color: #f87171; }
.we-field-exp { color: #22d3ee; }
.we-field-expc { color: #f87171; }
.we-field-opt { color: #9ca3af; }
.we-field-optc { color: #f87171; }

/* Character value reference */
.charval-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(52px, 1fr));
  gap: 4px;
  margin: 12px 0;
}
.charval-cell {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 4px;
  padding: 6px 4px;
  text-align: center;
}
.charval-char {
  font-family: 'Courier New', monospace;
  font-size: 15px;
  font-weight: 700;
  color: #fb923c;
}
.charval-num {
  font-size: 11px;
  color: #64748b;
}

/* Reference tables */
.ref-table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
}
.ref-table th {
  background: #1e293b;
  color: #94a3b8;
  text-align: left;
  padding: 8px 10px;
  border: 1px solid #334155;
  font-weight: 600;
}
.ref-table td {
  padding: 6px 10px;
  border: 1px solid #1e293b;
  color: #cbd5e1;
}
.ref-table tr:hover td {
  background: #1e293b;
}

/* Responsive */
@media (max-width: 600px) {
  #mrz-guide-root { padding: 12px 8px; }
  .mrz-line { font-size: 11px; letter-spacing: 0.5px; }
  .format-grid { grid-template-columns: 1fr 1fr; }
  .calc-cell { min-width: 32px; padding: 4px 3px; }
  .charval-grid { grid-template-columns: repeat(auto-fill, minmax(44px, 1fr)); }
}
</style>

<!-- ============================================ -->
<!-- SECTION 1: What is MRZ? -->
<!-- ============================================ -->
<h2>What is MRZ?</h2>
<p>
  The <strong>Machine Readable Zone (MRZ)</strong> is the standardized text block
  printed at the bottom of passports, ID cards, visas, and travel documents.
  Defined by <strong>ICAO Document 9303</strong> (the international standard for
  machine-readable travel documents), it encodes identity data in a fixed-width
  format optimized for OCR scanning.
</p>
<p>
  MRZ text uses the <strong>OCR-B font</strong>, specifically designed for
  reliable optical character recognition. The character set is limited to
  <strong>A&ndash;Z</strong>, <strong>0&ndash;9</strong>, and the
  <strong>&lt;</strong> filler character. The <code>&lt;</code> symbol replaces
  spaces and pads fields to their exact required lengths.
</p>
<p>
  <strong>Check digits</strong> are single digits computed from data fields using
  a weighted-sum algorithm. They allow machines to detect OCR misreads and
  tampering without querying a database.
</p>

<h3>MRZ Formats</h3>
<p>ICAO 9303 defines five MRZ formats:</p>
<div class="format-grid">
  <div class="format-item">
    <div class="fmt-name">TD1</div>
    <div class="fmt-dims">3 lines &times; 30 chars</div>
    <div class="fmt-use">ID cards, PR cards</div>
  </div>
  <div class="format-item">
    <div class="fmt-name">TD2</div>
    <div class="fmt-dims">2 lines &times; 36 chars</div>
    <div class="fmt-use">Older ID cards</div>
  </div>
  <div class="format-item">
    <div class="fmt-name">TD3</div>
    <div class="fmt-dims">2 lines &times; 44 chars</div>
    <div class="fmt-use">Passports</div>
  </div>
  <div class="format-item">
    <div class="fmt-name">MRV-A</div>
    <div class="fmt-dims">2 lines &times; 44 chars</div>
    <div class="fmt-use">Visa (full-page)</div>
  </div>
  <div class="format-item">
    <div class="fmt-name">MRV-B</div>
    <div class="fmt-dims">2 lines &times; 36 chars</div>
    <div class="fmt-use">Visa (compact)</div>
  </div>
</div>

<!-- Legend (shared across all breakdowns) -->
<div class="mrz-legend">
  <div class="mrz-legend-item"><span class="mrz-legend-dot" style="background:#60a5fa"></span>Doc Type</div>
  <div class="mrz-legend-item"><span class="mrz-legend-dot" style="background:#34d399"></span>Country</div>
  <div class="mrz-legend-item"><span class="mrz-legend-dot" style="background:#c084fc"></span>Name</div>
  <div class="mrz-legend-item"><span class="mrz-legend-dot" style="background:#fb923c"></span>Doc Number</div>
  <div class="mrz-legend-item"><span class="mrz-legend-dot" style="background:#f87171"></span>Check Digit</div>
  <div class="mrz-legend-item"><span class="mrz-legend-dot" style="background:#2dd4bf"></span>Nationality</div>
  <div class="mrz-legend-item"><span class="mrz-legend-dot" style="background:#fbbf24"></span>DOB</div>
  <div class="mrz-legend-item"><span class="mrz-legend-dot" style="background:#f472b6"></span>Sex</div>
  <div class="mrz-legend-item"><span class="mrz-legend-dot" style="background:#22d3ee"></span>Expiry</div>
  <div class="mrz-legend-item"><span class="mrz-legend-dot" style="background:#9ca3af"></span>Optional</div>
</div>

<!-- ============================================ -->
<!-- SECTION 2: TD3 Passport Breakdown -->
<!-- ============================================ -->
<h2>TD3 &mdash; Canadian Passport (2 &times; 44)</h2>
<p>Click or hover on any field to see what it means.</p>
<div class="mrz-box" id="td3-box">
  <div class="mrz-box-label">Line 1 &mdash; Identity</div>
  <div class="mrz-line"><!--
    --><span class="mrz-field mrz-doc-type" data-label="Document Type" data-value="P&lt;" data-desc="P = Passport. The &lt; is a filler character.">P&lt;</span><!--
    --><span class="mrz-field mrz-country" data-label="Issuing Country" data-value="CAN" data-desc="Three-letter ICAO country code. CAN = Canada.">CAN</span><!--
    --><span class="mrz-field mrz-name" data-label="Name" data-value="TREMBLAY&lt;&lt;MARIE&lt;CLAIRE" data-desc="Surname &lt;&lt; Given Names. Spaces become &lt;, double &lt;&lt; separates surname from given names.">TREMBLAY&lt;&lt;MARIE&lt;CLAIRE&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</span><!--
  --></div>
  <div class="mrz-box-label" style="margin-top:8px">Line 2 &mdash; Data + Check Digits</div>
  <div class="mrz-line"><!--
    --><span class="mrz-field mrz-doc-num" data-label="Document Number" data-value="AB1234567" data-desc="Alphanumeric passport number, up to 9 characters.">AB1234567</span><!--
    --><span class="mrz-field mrz-check" data-label="Check Digit (Doc Number)" data-value="1" data-desc="ICAO check digit for AB1234567. Computed: 1.">1</span><!--
    --><span class="mrz-field mrz-nationality" data-label="Nationality" data-value="CAN" data-desc="Holder's nationality. CAN = Canadian citizen.">CAN</span><!--
    --><span class="mrz-field mrz-dob" data-label="Date of Birth" data-value="850320" data-desc="YYMMDD format. 850320 = March 20, 1985.">850320</span><!--
    --><span class="mrz-field mrz-check" data-label="Check Digit (DOB)" data-value="8" data-desc="ICAO check digit for 850320. Computed: 8.">8</span><!--
    --><span class="mrz-field mrz-sex" data-label="Sex" data-value="F" data-desc="F = Female. M = Male, X = Unspecified.">F</span><!--
    --><span class="mrz-field mrz-expiry" data-label="Expiry Date" data-value="340320" data-desc="YYMMDD format. 340320 = March 20, 2034.">340320</span><!--
    --><span class="mrz-field mrz-check" data-label="Check Digit (Expiry)" data-value="0" data-desc="ICAO check digit for 340320. Computed: 0.">0</span><!--
    --><span class="mrz-field mrz-personal" data-label="Personal Number" data-value="&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;" data-desc="Optional personal number field (14 chars). Usually empty (all filler).">&#60;&#60;&#60;&#60;&#60;&#60;&#60;&#60;&#60;&#60;&#60;&#60;&#60;&#60;</span><!--
    --><span class="mrz-field mrz-check" data-label="Check Digit (Personal)" data-value="0" data-desc="ICAO check digit for the personal number field. All fillers = 0.">0</span><!--
    --><span class="mrz-field mrz-check" data-label="Overall Check Digit" data-value="0" data-desc="Composite check digit over: doc_num + doc_check + dob + dob_check + expiry + exp_check + personal + per_check. Computed: 0.">0</span><!--
  --></div>
  <div class="mrz-info" id="td3-info">
    <div class="mrz-info-hint">Hover or click a field above to see details</div>
  </div>
  <button class="mrz-btn" onclick="mrzAnimate('td3-box')">Replay Animation</button>
</div>

<!-- ============================================ -->
<!-- SECTION 3: TD1 PR Card Breakdown -->
<!-- ============================================ -->
<h2>TD1 &mdash; Canadian PR Card (3 &times; 30)</h2>
<p>Note: On PR cards, the issuing country is CAN but nationality reflects the holder's citizenship.</p>
<div class="mrz-box" id="td1-box">
  <div class="mrz-box-label">Line 1 &mdash; Document Info</div>
  <div class="mrz-line"><!--
    --><span class="mrz-field mrz-doc-type" data-label="Document Type" data-value="I&lt;" data-desc="I = ID card / PR card. The &lt; is a filler.">I&lt;</span><!--
    --><span class="mrz-field mrz-country" data-label="Issuing Country" data-value="CAN" data-desc="CAN = Canada. Always CAN for Canadian-issued documents.">CAN</span><!--
    --><span class="mrz-field mrz-doc-num" data-label="Document Number" data-value="PD0183017" data-desc="PR card number, up to 9 characters.">PD0183017</span><!--
    --><span class="mrz-field mrz-check" data-label="Check Digit (Doc Number)" data-value="8" data-desc="ICAO check digit for PD0183017. Computed: 8.">8</span><!--
    --><span class="mrz-field mrz-optional" data-label="Optional Data 1" data-value="&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;" data-desc="UCI number or province code (15 chars). Empty = all filler.">&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</span><!--
  --></div>
  <div class="mrz-box-label" style="margin-top:8px">Line 2 &mdash; Dates + Nationality</div>
  <div class="mrz-line"><!--
    --><span class="mrz-field mrz-dob" data-label="Date of Birth" data-value="841127" data-desc="YYMMDD. 841127 = November 27, 1984.">841127</span><!--
    --><span class="mrz-field mrz-check" data-label="Check Digit (DOB)" data-value="9" data-desc="ICAO check digit for 841127. Computed: 9.">9</span><!--
    --><span class="mrz-field mrz-sex" data-label="Sex" data-value="F" data-desc="F = Female. M = Male, X = Unspecified.">F</span><!--
    --><span class="mrz-field mrz-expiry" data-label="Expiry Date" data-value="260430" data-desc="YYMMDD. 260430 = April 30, 2026.">260430</span><!--
    --><span class="mrz-field mrz-check" data-label="Check Digit (Expiry)" data-value="9" data-desc="ICAO check digit for 260430. Computed: 9.">9</span><!--
    --><span class="mrz-field mrz-nationality" data-label="Nationality" data-value="CMR" data-desc="Holder's nationality. CMR = Cameroon. PR card holders keep their original nationality.">CMR</span><!--
    --><span class="mrz-field mrz-optional" data-label="Optional Data 2" data-value="&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;" data-desc="Additional optional data (11 chars). Usually empty.">&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</span><!--
    --><span class="mrz-field mrz-check" data-label="Overall Check Digit" data-value="8" data-desc="Composite check digit over: doc_num + doc_check + opt1 + dob + dob_check + expiry + exp_check + opt2. Computed: 8.">8</span><!--
  --></div>
  <div class="mrz-box-label" style="margin-top:8px">Line 3 &mdash; Name</div>
  <div class="mrz-line"><!--
    --><span class="mrz-field mrz-name" data-label="Name" data-value="MAGHA&lt;MOFFO&lt;&lt;MATHILDE" data-desc="Surname &lt;&lt; Given Names. Full 30-character name field.">MAGHA&lt;MOFFO&lt;&lt;MATHILDE&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</span><!--
  --></div>
  <div class="mrz-info" id="td1-info">
    <div class="mrz-info-hint">Hover or click a field above to see details</div>
  </div>
  <button class="mrz-btn" onclick="mrzAnimate('td1-box')">Replay Animation</button>
</div>

<!-- ============================================ -->
<!-- SECTION 4: TD2 Breakdown -->
<!-- ============================================ -->
<h2>TD2 &mdash; ID Document (2 &times; 36)</h2>
<p>TD2 is a 2-line format with 36 characters per line, used for some national ID cards.</p>
<div class="mrz-box" id="td2-box">
  <div class="mrz-box-label">Line 1 &mdash; Identity</div>
  <div class="mrz-line"><!--
    --><span class="mrz-field mrz-doc-type" data-label="Document Type" data-value="I&lt;" data-desc="I = ID document. The &lt; is a filler.">I&lt;</span><!--
    --><span class="mrz-field mrz-country" data-label="Issuing Country" data-value="CAN" data-desc="CAN = Canada.">CAN</span><!--
    --><span class="mrz-field mrz-name" data-label="Name" data-value="SINGH&lt;&lt;HARPREET" data-desc="Surname &lt;&lt; Given Names. Padded with &lt; to fill 31 characters.">SINGH&lt;&lt;HARPREET&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</span><!--
  --></div>
  <div class="mrz-box-label" style="margin-top:8px">Line 2 &mdash; Data + Check Digits</div>
  <div class="mrz-line"><!--
    --><span class="mrz-field mrz-doc-num" data-label="Document Number" data-value="D12345678" data-desc="Document number, 9 characters.">D12345678</span><!--
    --><span class="mrz-field mrz-check" data-label="Check Digit (Doc Number)" data-value="5" data-desc="ICAO check digit for D12345678. Computed: 5.">5</span><!--
    --><span class="mrz-field mrz-nationality" data-label="Nationality" data-value="CAN" data-desc="Holder's nationality. CAN = Canadian.">CAN</span><!--
    --><span class="mrz-field mrz-dob" data-label="Date of Birth" data-value="880515" data-desc="YYMMDD. 880515 = May 15, 1988.">880515</span><!--
    --><span class="mrz-field mrz-check" data-label="Check Digit (DOB)" data-value="3" data-desc="ICAO check digit for 880515. Computed: 3.">3</span><!--
    --><span class="mrz-field mrz-sex" data-label="Sex" data-value="M" data-desc="M = Male. F = Female, X = Unspecified.">M</span><!--
    --><span class="mrz-field mrz-expiry" data-label="Expiry Date" data-value="290515" data-desc="YYMMDD. 290515 = May 15, 2029.">290515</span><!--
    --><span class="mrz-field mrz-check" data-label="Check Digit (Expiry)" data-value="4" data-desc="ICAO check digit for 290515. Computed: 4.">4</span><!--
    --><span class="mrz-field mrz-optional" data-label="Optional Data" data-value="&lt;&lt;&lt;&lt;&lt;&lt;&lt;" data-desc="Optional data field (7 chars). Usually empty.">&lt;&lt;&lt;&lt;&lt;&lt;&lt;</span><!--
    --><span class="mrz-field mrz-check" data-label="Overall Check Digit" data-value="8" data-desc="Composite check digit over: doc_num + doc_check + dob + dob_check + expiry + exp_check + optional. Computed: 8.">8</span><!--
  --></div>
  <div class="mrz-info" id="td2-info">
    <div class="mrz-info-hint">Hover or click a field above to see details</div>
  </div>
  <button class="mrz-btn" onclick="mrzAnimate('td2-box')">Replay Animation</button>
</div>

<!-- ============================================ -->
<!-- SECTION 5: Live Check Digit Calculator -->
<!-- ============================================ -->
<h2>Live Check Digit Calculator</h2>
<p>
  Type any MRZ data string (A&ndash;Z, 0&ndash;9, &lt;) and see the ICAO check
  digit computed live. Each character is assigned a numeric value, multiplied by a
  cycling weight (7, 3, 1), and the sum mod 10 gives the check digit.
</p>
<div class="mrz-card">
  <input type="text" id="calc-input" class="calc-input" value="AB1234567"
    placeholder="Type MRZ data (A-Z, 0-9, <)" maxlength="44"
    autocomplete="off" spellcheck="false">
  <div id="calc-grid" class="calc-grid"></div>
  <div id="calc-result" class="calc-result"></div>
  <div style="margin-top:12px">
    <button class="mrz-btn-primary" id="calc-play-btn" onclick="calcPlayAnim()">
      Play Step-by-Step</button>
  </div>
</div>

<!-- ============================================ -->
<!-- SECTION 6: Worked Examples -->
<!-- ============================================ -->
<h2>Worked Examples &mdash; Composite Check Digits</h2>
<p>
  Each MRZ format has an <strong>overall (composite) check digit</strong> that
  covers multiple data fields concatenated together. Here is the formula for each.
</p>

<h3>TD3 &mdash; Overall Check Digit</h3>
<p>The composite string is: <strong>doc_num + doc_check + dob + dob_check + expiry + exp_check + personal + per_check</strong></p>
<div class="we-formula"><span class="we-field we-field-dn">AB1234567</span><span class="we-field we-field-dc">1</span><span class="we-field we-field-dob">850320</span><span class="we-field we-field-dobc">8</span><span class="we-field we-field-exp">340320</span><span class="we-field we-field-expc">0</span><span class="we-field we-field-opt">&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</span><span class="we-field we-field-optc">0</span>
= <span style="color:#f87171;font-weight:700">AB1234567185032083403200&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;0</span>
ICAO check digit = <span style="color:#f87171;font-weight:700;font-size:16px">0</span></div>

<h3>TD1 &mdash; Overall Check Digit</h3>
<p>The composite string is: <strong>doc_num + doc_check + opt1 + dob + dob_check + expiry + exp_check + opt2</strong></p>
<div class="we-formula"><span class="we-field we-field-dn">PD0183017</span><span class="we-field we-field-dc">8</span><span class="we-field we-field-opt">&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</span><span class="we-field we-field-dob">841127</span><span class="we-field we-field-dobc">9</span><span class="we-field we-field-exp">260430</span><span class="we-field we-field-expc">9</span><span class="we-field we-field-opt">&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</span>
= <span style="color:#f87171;font-weight:700">PD01830178&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;84112792604309&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;&lt;</span>
ICAO check digit = <span style="color:#f87171;font-weight:700;font-size:16px">8</span></div>

<h3>TD2 &mdash; Overall Check Digit</h3>
<p>The composite string is: <strong>doc_num + doc_check + dob + dob_check + expiry + exp_check + optional</strong></p>
<div class="we-formula"><span class="we-field we-field-dn">D12345678</span><span class="we-field we-field-dc">5</span><span class="we-field we-field-dob">880515</span><span class="we-field we-field-dobc">3</span><span class="we-field we-field-exp">290515</span><span class="we-field we-field-expc">4</span><span class="we-field we-field-opt">&lt;&lt;&lt;&lt;&lt;&lt;&lt;</span>
= <span style="color:#f87171;font-weight:700">D12345678588051532905154&lt;&lt;&lt;&lt;&lt;&lt;&lt;</span>
ICAO check digit = <span style="color:#f87171;font-weight:700;font-size:16px">8</span></div>

<!-- ============================================ -->
<!-- SECTION 7: Character Value Reference Table -->
<!-- ============================================ -->
<h2>Character Value Reference</h2>
<p>ICAO 9303 assigns each character a numeric value for check digit computation.</p>
<div class="charval-grid" id="charval-grid"></div>

<!-- ============================================ -->
<!-- SECTION 8: Quick Reference Tables -->
<!-- ============================================ -->
<h2>Quick Reference &mdash; Field Positions</h2>

<h3>TD1 &mdash; ID / PR Card (3 &times; 30)</h3>
<table class="ref-table">
  <tr><th>Line</th><th>Pos</th><th>Len</th><th>Field</th><th>Notes</th></tr>
  <tr><td>1</td><td>1&ndash;2</td><td>2</td><td>Document Type</td><td>I for ID/PR card</td></tr>
  <tr><td>1</td><td>3&ndash;5</td><td>3</td><td>Issuing Country</td><td>CAN</td></tr>
  <tr><td>1</td><td>6&ndash;14</td><td>9</td><td>Document Number</td><td>Alphanumeric</td></tr>
  <tr><td>1</td><td>15</td><td>1</td><td>Check Digit</td><td>For doc number</td></tr>
  <tr><td>1</td><td>16&ndash;30</td><td>15</td><td>Optional Data 1</td><td>UCI / province</td></tr>
  <tr><td>2</td><td>1&ndash;6</td><td>6</td><td>Date of Birth</td><td>YYMMDD</td></tr>
  <tr><td>2</td><td>7</td><td>1</td><td>Check Digit</td><td>For DOB</td></tr>
  <tr><td>2</td><td>8</td><td>1</td><td>Sex</td><td>M / F / X</td></tr>
  <tr><td>2</td><td>9&ndash;14</td><td>6</td><td>Expiry Date</td><td>YYMMDD</td></tr>
  <tr><td>2</td><td>15</td><td>1</td><td>Check Digit</td><td>For expiry</td></tr>
  <tr><td>2</td><td>16&ndash;18</td><td>3</td><td>Nationality</td><td>3-letter code</td></tr>
  <tr><td>2</td><td>19&ndash;29</td><td>11</td><td>Optional Data 2</td><td>Additional data</td></tr>
  <tr><td>2</td><td>30</td><td>1</td><td>Overall Check</td><td>Composite</td></tr>
  <tr><td>3</td><td>1&ndash;30</td><td>30</td><td>Name</td><td>SURNAME&lt;&lt;GIVEN</td></tr>
</table>

<h3>TD2 &mdash; ID Document (2 &times; 36)</h3>
<table class="ref-table">
  <tr><th>Line</th><th>Pos</th><th>Len</th><th>Field</th><th>Notes</th></tr>
  <tr><td>1</td><td>1&ndash;2</td><td>2</td><td>Document Type</td><td>I or A/C</td></tr>
  <tr><td>1</td><td>3&ndash;5</td><td>3</td><td>Issuing Country</td><td>3-letter code</td></tr>
  <tr><td>1</td><td>6&ndash;36</td><td>31</td><td>Name</td><td>SURNAME&lt;&lt;GIVEN</td></tr>
  <tr><td>2</td><td>1&ndash;9</td><td>9</td><td>Document Number</td><td>Alphanumeric</td></tr>
  <tr><td>2</td><td>10</td><td>1</td><td>Check Digit</td><td>For doc number</td></tr>
  <tr><td>2</td><td>11&ndash;13</td><td>3</td><td>Nationality</td><td>3-letter code</td></tr>
  <tr><td>2</td><td>14&ndash;19</td><td>6</td><td>Date of Birth</td><td>YYMMDD</td></tr>
  <tr><td>2</td><td>20</td><td>1</td><td>Check Digit</td><td>For DOB</td></tr>
  <tr><td>2</td><td>21</td><td>1</td><td>Sex</td><td>M / F / X</td></tr>
  <tr><td>2</td><td>22&ndash;27</td><td>6</td><td>Expiry Date</td><td>YYMMDD</td></tr>
  <tr><td>2</td><td>28</td><td>1</td><td>Check Digit</td><td>For expiry</td></tr>
  <tr><td>2</td><td>29&ndash;35</td><td>7</td><td>Optional Data</td><td>Additional data</td></tr>
  <tr><td>2</td><td>36</td><td>1</td><td>Overall Check</td><td>Composite</td></tr>
</table>

<h3>TD3 &mdash; Passport (2 &times; 44)</h3>
<table class="ref-table">
  <tr><th>Line</th><th>Pos</th><th>Len</th><th>Field</th><th>Notes</th></tr>
  <tr><td>1</td><td>1&ndash;2</td><td>2</td><td>Document Type</td><td>P for passport</td></tr>
  <tr><td>1</td><td>3&ndash;5</td><td>3</td><td>Issuing Country</td><td>3-letter code</td></tr>
  <tr><td>1</td><td>6&ndash;44</td><td>39</td><td>Name</td><td>SURNAME&lt;&lt;GIVEN&lt;NAMES</td></tr>
  <tr><td>2</td><td>1&ndash;9</td><td>9</td><td>Document Number</td><td>Alphanumeric</td></tr>
  <tr><td>2</td><td>10</td><td>1</td><td>Check Digit</td><td>For doc number</td></tr>
  <tr><td>2</td><td>11&ndash;13</td><td>3</td><td>Nationality</td><td>3-letter code</td></tr>
  <tr><td>2</td><td>14&ndash;19</td><td>6</td><td>Date of Birth</td><td>YYMMDD</td></tr>
  <tr><td>2</td><td>20</td><td>1</td><td>Check Digit</td><td>For DOB</td></tr>
  <tr><td>2</td><td>21</td><td>1</td><td>Sex</td><td>M / F / X</td></tr>
  <tr><td>2</td><td>22&ndash;27</td><td>6</td><td>Expiry Date</td><td>YYMMDD</td></tr>
  <tr><td>2</td><td>28</td><td>1</td><td>Check Digit</td><td>For expiry</td></tr>
  <tr><td>2</td><td>29&ndash;42</td><td>14</td><td>Personal Number</td><td>Optional</td></tr>
  <tr><td>2</td><td>43</td><td>1</td><td>Check Digit</td><td>For personal #</td></tr>
  <tr><td>2</td><td>44</td><td>1</td><td>Overall Check</td><td>Composite</td></tr>
</table>

<!-- ============================================ -->
<!-- JAVASCRIPT -->
<!-- ============================================ -->
<script>
(function() {
  var root = document.getElementById('mrz-guide-root');
  if (!root) return;

  /* ── ICAO character values ── */
  var CV = {};
  var i, c;
  for (i = 0; i <= 9; i++) CV[String(i)] = i;
  for (i = 0; i < 26; i++) {
    CV[String.fromCharCode(65 + i)] = i + 10;
  }
  CV['<'] = 0;
  var WEIGHTS = [7, 3, 1];

  function icaoCheck(text) {
    var total = 0;
    for (var j = 0; j < text.length; j++) {
      var ch = text.charAt(j).toUpperCase();
      var v = CV[ch];
      if (v === undefined) v = 0;
      total += v * WEIGHTS[j % 3];
    }
    return total % 10;
  }

  /* ── Build character value reference grid ── */
  var gridEl = document.getElementById('charval-grid');
  if (gridEl) {
    var chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ<';
    var html = '';
    for (i = 0; i < chars.length; i++) {
      c = chars.charAt(i);
      var display = c === '<' ? '&lt;' : c;
      html += '<div class="charval-cell"><div class="charval-char">' +
        display + '</div><div class="charval-num">= ' +
        CV[c] + '</div></div>';
    }
    gridEl.innerHTML = html;
  }

  /* ── Field hover/click interaction ── */
  var activeField = null;

  root.addEventListener('mouseover', function(e) {
    var f = e.target.closest('.mrz-field');
    if (!f) return;
    if (activeField && activeField !== f) return;
    showFieldInfo(f);
  });

  root.addEventListener('mouseout', function(e) {
    var f = e.target.closest('.mrz-field');
    if (!f || f === activeField) return;
    var box = f.closest('.mrz-box');
    if (box) resetFieldInfo(box);
  });

  root.addEventListener('click', function(e) {
    var f = e.target.closest('.mrz-field');
    if (!f) return;
    if (activeField === f) {
      f.classList.remove('active');
      activeField = null;
      var box = f.closest('.mrz-box');
      if (box) resetFieldInfo(box);
      return;
    }
    if (activeField) activeField.classList.remove('active');
    f.classList.add('active');
    activeField = f;
    showFieldInfo(f);
  });

  function showFieldInfo(f) {
    var box = f.closest('.mrz-box');
    if (!box) return;
    var info = box.querySelector('.mrz-info');
    if (!info) return;
    var label = f.getAttribute('data-label') || '';
    var value = f.getAttribute('data-value') || '';
    var desc = f.getAttribute('data-desc') || '';
    info.innerHTML =
      '<div class="mrz-info-label">' + label + '</div>' +
      '<div class="mrz-info-value">' + value + '</div>' +
      '<div class="mrz-info-desc">' + desc + '</div>';
  }

  function resetFieldInfo(box) {
    var info = box.querySelector('.mrz-info');
    if (info) {
      info.innerHTML =
        '<div class="mrz-info-hint">' +
        'Hover or click a field above to see details</div>';
    }
  }

  /* ── Cascade animation ── */
  window.mrzAnimate = function(boxId) {
    var box = document.getElementById(boxId);
    if (!box) return;
    var fields = box.querySelectorAll('.mrz-field');
    box.classList.remove('mrz-animating');
    void box.offsetWidth;
    for (var j = 0; j < fields.length; j++) {
      fields[j].style.animationDelay = (j * 50) + 'ms';
    }
    box.classList.add('mrz-animating');
  };

  /* Auto-animate on load */
  setTimeout(function() {
    mrzAnimate('td3-box');
    setTimeout(function() { mrzAnimate('td1-box'); }, 600);
    setTimeout(function() { mrzAnimate('td2-box'); }, 1200);
  }, 300);

  /* ── Live Check Digit Calculator ── */
  var calcInput = document.getElementById('calc-input');
  var calcGrid = document.getElementById('calc-grid');
  var calcResult = document.getElementById('calc-result');

  function renderCalc(text) {
    text = text.toUpperCase().replace(/[^A-Z0-9<]/g, '');
    if (!text) {
      calcGrid.innerHTML = '';
      calcResult.innerHTML = '<span style="color:#475569">Type characters above</span>';
      return;
    }
    var html = '';
    var total = 0;
    for (var j = 0; j < text.length; j++) {
      var ch = text.charAt(j);
      var v = CV[ch];
      if (v === undefined) v = 0;
      var w = WEIGHTS[j % 3];
      var prod = v * w;
      total += prod;
      var display = ch === '<' ? '&lt;' : ch;
      html += '<div class="calc-cell">' +
        '<div class="cc-char">' + display + '</div>' +
        '<div class="cc-val">val=' + v + '</div>' +
        '<div class="cc-wt">&times;' + w + '</div>' +
        '<div class="cc-prod">=' + prod + '</div></div>';
    }
    calcGrid.innerHTML = html;
    var result = total % 10;
    calcResult.innerHTML = 'Total: <strong>' + total +
      '</strong> mod 10 = <span class="calc-result-num">' +
      result + '</span>';
  }

  if (calcInput) {
    calcInput.addEventListener('input', function() {
      renderCalc(calcInput.value);
    });
    renderCalc(calcInput.value);
  }

  /* ── Step-by-step animation ── */
  var calcPlaying = false;

  window.calcPlayAnim = function() {
    if (calcPlaying) return;
    var text = calcInput.value.toUpperCase().replace(/[^A-Z0-9<]/g, '');
    if (!text) return;
    calcPlaying = true;
    var btn = document.getElementById('calc-play-btn');
    btn.disabled = true;

    /* Reset grid to empty state */
    var html = '';
    for (var j = 0; j < text.length; j++) {
      var ch = text.charAt(j);
      var display = ch === '<' ? '&lt;' : ch;
      html += '<div class="calc-cell" id="cc-' + j + '">' +
        '<div class="cc-char">' + display + '</div>' +
        '<div class="cc-val" style="visibility:hidden">val=0</div>' +
        '<div class="cc-wt" style="visibility:hidden">&times;0</div>' +
        '<div class="cc-prod" style="visibility:hidden">=0</div></div>';
    }
    calcGrid.innerHTML = html;
    calcResult.innerHTML = '';

    var step = 0;
    var total = 0;
    var interval = setInterval(function() {
      if (step > 0) {
        var prev = document.getElementById('cc-' + (step - 1));
        if (prev) {
          prev.classList.remove('calc-active');
          prev.classList.add('calc-done');
        }
      }
      if (step >= text.length) {
        clearInterval(interval);
        var result = total % 10;
        calcResult.innerHTML = 'Total: <strong>' + total +
          '</strong> mod 10 = <span class="calc-result-num">' +
          result + '</span>';
        btn.disabled = false;
        calcPlaying = false;
        return;
      }
      var cell = document.getElementById('cc-' + step);
      if (cell) {
        cell.classList.add('calc-active');
        var ch = text.charAt(step);
        var v = CV[ch];
        if (v === undefined) v = 0;
        var w = WEIGHTS[step % 3];
        var prod = v * w;
        total += prod;
        var children = cell.children;
        children[1].textContent = 'val=' + v;
        children[1].style.visibility = 'visible';
        children[2].innerHTML = '&times;' + w;
        children[2].style.visibility = 'visible';
        children[3].textContent = '=' + prod;
        children[3].style.visibility = 'visible';
      }
      step++;
    }, 300);
  };

})();
</script>

</div>
"""
