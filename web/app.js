(function () {
  "use strict";

  // ------------------------------------------------------------------ state
  var D = null;
  var IDX = {};
  var state = { tab: "overview", mask: true, scheme: "all", q: "", action: "all", sort: "score", limit: 50, legitType: "all", legitLimit: 50, chartView: "chart", selected: null };
  var EMERGENCY = { "112": "Единая служба спасения", "101": "Пожарная охрана", "102": "Полиция", "103": "Скорая помощь", "104": "Газовая служба" };
  var OPS = { "842": "Городской", "499": "Городской", "892": "Городской", "025": "Альфа", "026": "Альфа", "027": "Альфа", "899": "Барбетта", "810": "Барбетта", "834": "Барбетта", "210": "Bell-ka", "214": "Bell-ka", "200": "Bell-ka" };
  var DAYS = ["вс", "пн", "вт", "ср", "чт", "пт", "сб"];
  var ROLE_FORMS = {
    initiator: ["номер-приманка", "номера-приманки", "номеров-приманок"], premium: ["платный номер", "платных номера", "платных номеров"],
    fraudster: ["мошенник", "мошенника", "мошенников"], spoof: ["спуф-номер", "спуф-номера", "спуф-номеров"]
  };
  var GROUP_FORMS = { S2: ["связка", "связки", "связок"], S5: ["маршрут", "маршрута", "маршрутов"], S6: ["группа", "группы", "групп"] };
  var MONTHS = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];

  var ICON = {
    block: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="8" cy="8" r="6"/><path d="M3.8 3.8l8.4 8.4"/></svg>',
    flag: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M3.5 14V2.5h8l-1.6 3 1.6 3h-8"/></svg>',
    review: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L14 14"/></svg>',
    watch: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M1.5 8s2.4-4.5 6.5-4.5S14.5 8 14.5 8 12.1 12.5 8 12.5 1.5 8 1.5 8z"/><circle cx="8" cy="8" r="1.8"/></svg>',
    allow: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8.5l3.2 3.2L13 4.8"/></svg>',
    never_block: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M8 1.8l5 1.8v4.2c0 3-2.1 5.3-5 6.4-2.9-1.1-5-3.4-5-6.4V3.6z"/><path d="M8 5.2v5M5.5 7.7h5"/></svg>',
    x: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M3.5 3.5l9 9M12.5 3.5l-9 9"/></svg>',
    search: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5L14 14"/></svg>',
    postmark: '<svg viewBox="0 0 44 30" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="13" cy="15" r="11"/><circle cx="13" cy="15" r="7.5"/><path d="M26 8c3 0 3 2.4 6 2.4S35 8 38 8s3 2.4 6 2.4M26 14c3 0 3 2.4 6 2.4s3-2.4 6-2.4 3 2.4 6 2.4M26 20c3 0 3 2.4 6 2.4s3-2.4 6-2.4 3 2.4 6 2.4"/></svg>'
  };

  // пиктограммы механики каждой схемы
  var PICTO = {
    S1: '<circle cx="10" cy="22" r="5" fill="currentColor"/><g stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M18 22h9M18 16l8-6M18 28l8 6M17 12l4-7M17 32l4 7"/></g><path d="M64 22c-10-12-26-12-34-3" fill="none" stroke="currentColor" stroke-width="1.6" stroke-dasharray="3 3"/><circle cx="66" cy="22" r="6" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M66 19v6M63.8 22h4.4" stroke="currentColor" stroke-width="1.4"/>',
    S2: '<g fill="currentColor"><rect x="4" y="16" width="5" height="12" rx="1"/><rect x="13" y="16" width="5" height="12" rx="1"/><rect x="22" y="16" width="5" height="12" rx="1"/><rect x="31" y="16" width="5" height="12" rx="1"/><rect x="40" y="16" width="5" height="12" rx="1"/></g><g fill="none" stroke="currentColor" stroke-width="1.4"><rect x="49" y="16" width="5" height="12" rx="1"/><rect x="58" y="16" width="5" height="12" rx="1"/><rect x="67" y="16" width="5" height="12" rx="1"/></g><path d="M4 36h60m-5-4l5 4-5 4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>',
    S3: '<rect x="6" y="6" width="64" height="32" rx="3" fill="none" stroke="currentColor" stroke-width="1.6"/><g fill="currentColor"><path d="M13 13h8l3 3v15H13z"/><path d="M28 13h8l3 3v15H28z"/><path d="M43 13h8l3 3v15H43z"/></g><path d="M58 13h8v18h-8z" fill="none" stroke="currentColor" stroke-width="1.4"/>',
    S4: '<g fill="none" stroke="currentColor" stroke-width="1.6"><path d="M30 10h14l5 5v21H30z" opacity="0.45"/><path d="M22 7h14l5 5v21H22z" opacity="0.7"/></g><path d="M14 4h14l5 5v21H14z" fill="currentColor"/><path d="M52 22h18M52 28h12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
    S5: '<g fill="currentColor"><circle cx="9" cy="14" r="4.5"/><circle cx="29" cy="14" r="4.5"/><circle cx="49" cy="14" r="4.5"/><circle cx="69" cy="14" r="4.5"/></g><g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14h8M35 14h8M55 14h8"/><path d="M69 20v10a6 6 0 01-6 6H15a6 6 0 01-6-6v-9m-4 4l4-4 4 4"/></g>',
    S6: '<g fill="none" stroke="currentColor" stroke-width="1.3" opacity="0.6"><path d="M38 5l15 9v16l-15 9-15-9V14zM38 5v34M23 14l30 16M53 14L23 30"/></g><g fill="currentColor"><circle cx="38" cy="5" r="4"/><circle cx="53" cy="14" r="4"/><circle cx="53" cy="30" r="4"/><circle cx="38" cy="39" r="4"/><circle cx="23" cy="30" r="4"/><circle cx="23" cy="14" r="4"/></g>',
    S7: '<g fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="8" cy="7" r="3.5"/><circle cx="8" cy="18" r="3.5"/><circle cx="8" cy="29" r="3.5"/><circle cx="8" cy="40" r="3.5"/><path d="M13 8l14 10M13 18h14M13 29l14-8M13 39l15-17" stroke-dasharray="2 3"/></g><circle cx="33" cy="20" r="5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M40 20h22" stroke="currentColor" stroke-width="4" stroke-linecap="round"/><circle cx="68" cy="20" r="6" fill="currentColor"/>'
  };

  // ------------------------------------------------------------------ helpers
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function nf(n) { return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " "); }
  function plural(n, forms) {
    var a = Math.abs(n) % 100, b = a % 10;
    return forms[(b === 1 && a !== 11) ? 0 : (b >= 2 && b <= 4 && (a < 12 || a > 14)) ? 1 : 2];
  }
  function pc(x, d) { return (100 * x).toFixed(d || 0).replace(".", ",") + "%"; }
  function operator(num) { return (num && OPS[num.slice(0, 3)]) || (EMERGENCY[num] ? "Экстренная служба" : "Неизвестный оператор"); }
  function showNum(num) {
    if (!num) return "—";
    if (num.length !== 10) return num;
    return state.mask ? "+7 " + num.slice(0, 3) + " ***-**-" + num.slice(-2)
                      : "+7 " + num.slice(0, 3) + " " + num.slice(3, 6) + "-" + num.slice(6, 8) + "-" + num.slice(8);
  }
  function rawNum(num) { return state.mask && num && num.length === 10 ? num.slice(0, 3) + "*****" + num.slice(-2) : (num || ""); }
  function schemeMeta(code) { return D.schemes.fraud[code] || D.schemes.legit[code] || { title: code }; }
  function isLegit(card) { return card.scheme.charAt(0) === "D"; }
  function schemeColor(code) { return code.charAt(0) === "S" ? "var(--s" + code.slice(1) + ")" : "var(--good)"; }
  function sevColor(card) {
    if (isLegit(card)) return "var(--good)";
    var s = card.score;
    return s >= 90 ? "var(--critical)" : s >= 75 ? "var(--serious)" : s >= 60 ? "var(--warning)" : "var(--muted)";
  }
  function sevLight(card) { return !isLegit(card) && card.score >= 60 && card.score < 90; } // тёмный текст на жёлтом/оранжевом штампе
  function hourLabel(i) {
    var t = new Date(D.meta.hour0.replace(" ", "T"));
    t.setHours(t.getHours() + i);
    return DAYS[t.getDay()] + " " + t.getDate() + " " + MONTHS[t.getMonth()] + ", " + ("0" + t.getHours()).slice(-2) + ":00";
  }
  function dayLabel(i) {
    var t = new Date(D.meta.hour0.replace(" ", "T"));
    t.setHours(t.getHours() + i);
    return DAYS[t.getDay()] + " " + t.getDate() + " " + MONTHS[t.getMonth()];
  }
  function ts(s) { return s ? s.slice(8, 10) + "." + s.slice(5, 7) + " " + s.slice(11, 16) : "—"; }
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

  // ------------------------------------------------------------------ charts
  function niceMax(v) {
    if (v <= 0) return 1;
    var p = Math.pow(10, Math.floor(Math.log10(v))), m = v / p;
    return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p;
  }
  function compact(v) { return v >= 1000 ? (v / 1000).toString().replace(".", ",") + "K" : String(v); }

  function areaChart(box, values, opt) {
    var W = Math.max(280, box.clientWidth), H = opt.height || 150, m = { l: 40, r: 14, t: 18, b: 22 };
    var iw = W - m.l - m.r, ih = H - m.t - m.b, n = values.length;
    var ymax = niceMax(Math.max.apply(null, values));
    var x = function (i) { return m.l + (n === 1 ? 0 : i * iw / (n - 1)); };
    var y = function (v) { return m.t + ih - v / ymax * ih; };
    var line = values.map(function (v, i) { return (i ? "L" : "M") + x(i).toFixed(1) + " " + y(v).toFixed(1); }).join("");
    var area = line + "L" + x(n - 1).toFixed(1) + " " + y(0) + "L" + x(0) + " " + y(0) + "Z";
    var grid = "", ticks = "";
    [0, 0.5, 1].forEach(function (f) {
      var yy = y(ymax * f);
      if (f) grid += '<line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + yy + '" y2="' + yy + '"/>';
      ticks += '<text x="' + (m.l - 8) + '" y="' + (yy + 4) + '" text-anchor="end">' + compact(ymax * f) + "</text>";
    });
    var days = "";
    for (var h = 0; h < n; h += 24) {
      days += '<line class="base" x1="' + x(h) + '" x2="' + x(h) + '" y1="' + y(0) + '" y2="' + (y(0) + 4) + '"/>' +
              '<text x="' + (x(h) + 4) + '" y="' + (H - 4) + '">' + dayLabel(h) + "</text>";
    }
    var pk = values.indexOf(Math.max.apply(null, values));
    var anchor = x(pk) > W - 150 ? "end" : "start", dx = anchor === "end" ? -8 : 8;
    box.innerHTML =
      '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + esc(opt.label) + '">' +
      '<g class="grid">' + grid + "</g>" +
      '<path d="' + area + '" style="fill:' + opt.color + ';opacity:0.10"/>' +
      '<path d="' + line + '" fill="none" style="stroke:' + opt.color + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>' +
      '<line class="base" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + y(0) + '" y2="' + y(0) + '"/>' +
      '<g class="axis">' + ticks + days + "</g>" +
      '<g class="peak"><circle cx="' + x(pk) + '" cy="' + y(values[pk]) + '" r="4" style="fill:' + opt.color + ';stroke:var(--surface)" stroke-width="2"/>' +
      '<text x="' + (x(pk) + dx) + '" y="' + (y(values[pk]) - 6) + '" text-anchor="' + anchor + '">пик ' + nf(values[pk]) + "</text></g>" +
      '<g class="hover" hidden><line class="base" y1="' + m.t + '" y2="' + y(0) + '"/><circle r="4" style="fill:' + opt.color + ';stroke:var(--surface)" stroke-width="2"/></g>' +
      '<rect x="' + m.l + '" y="' + m.t + '" width="' + iw + '" height="' + ih + '" fill="transparent"/></svg><div class="tip" hidden></div>';
    var svg = $("svg", box), hov = $(".hover", box), tip = $(".tip", box);
    function move(ev) {
      var r = svg.getBoundingClientRect(), px = (ev.clientX - r.left) * (W / r.width);
      var i = Math.max(0, Math.min(n - 1, Math.round((px - m.l) / iw * (n - 1))));
      hov.removeAttribute("hidden");
      $("line", hov).setAttribute("x1", x(i)); $("line", hov).setAttribute("x2", x(i));
      $("circle", hov).setAttribute("cx", x(i)); $("circle", hov).setAttribute("cy", y(values[i]));
      tip.hidden = false;
      tip.innerHTML = hourLabel(i) + "<br><b>" + nf(values[i]) + "</b> " + esc(opt.unit);
      var left = x(i) * (r.width / W);
      tip.style.left = Math.max(70, Math.min(r.width - 70, left)) + "px";
      tip.style.top = (y(values[i]) * (r.height / H) - 10) + "px";
    }
    svg.addEventListener("pointermove", move);
    svg.addEventListener("pointerleave", function () { hov.setAttribute("hidden", ""); tip.hidden = true; });
  }

  function columnChart(box, values, color) {
    var W = Math.max(280, box.clientWidth), H = 110, m = { l: 32, r: 6, t: 10, b: 22 };
    var iw = W - m.l - m.r, ih = H - m.t - m.b, n = values.length, bw = iw / n;
    var ymax = niceMax(Math.max.apply(null, values.concat([1])));
    var bars = "", days = "";
    values.forEach(function (v, i) {
      if (!v) return;
      var hh = Math.max(1.5, v / ymax * ih);
      bars += '<rect x="' + (m.l + i * bw + 0.5).toFixed(1) + '" y="' + (m.t + ih - hh).toFixed(1) + '" width="' + Math.max(1, bw - 1).toFixed(1) +
              '" height="' + hh.toFixed(1) + '" rx="1" style="fill:' + color + '"/>';
    });
    for (var h = 0; h < n; h += 24) {
      days += '<line class="base" x1="' + (m.l + h * bw) + '" x2="' + (m.l + h * bw) + '" y1="' + (m.t + ih) + '" y2="' + (m.t + ih + 4) + '"/>' +
              '<text x="' + (m.l + h * bw + 3) + '" y="' + (H - 4) + '">' + dayLabel(h) + "</text>";
    }
    box.innerHTML =
      '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Исходящие вызовы номера по часам">' +
      '<g class="grid"><line x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + m.t + '" y2="' + m.t + '"/></g>' + bars +
      '<line class="base" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + (m.t + ih) + '" y2="' + (m.t + ih) + '"/>' +
      '<g class="axis"><text x="' + (m.l - 6) + '" y="' + (m.t + 4) + '" text-anchor="end">' + compact(ymax) + '</text><text x="' + (m.l - 6) + '" y="' + (m.t + ih + 4) + '" text-anchor="end">0</text>' + days + "</g>" +
      '<rect x="' + m.l + '" y="' + m.t + '" width="' + iw + '" height="' + ih + '" fill="transparent"/></svg><div class="tip" hidden></div>';
    var svg = $("svg", box), tip = $(".tip", box);
    svg.addEventListener("pointermove", function (ev) {
      var r = svg.getBoundingClientRect(), px = (ev.clientX - r.left) * (W / r.width);
      var i = Math.max(0, Math.min(n - 1, Math.floor((px - m.l) / bw)));
      tip.hidden = false;
      tip.innerHTML = hourLabel(i) + "<br><b>" + nf(values[i]) + "</b> " + plural(values[i], ["вызов", "вызова", "вызовов"]);
      tip.style.left = Math.max(70, Math.min(r.width - 70, (m.l + (i + 0.5) * bw) * (r.width / W))) + "px";
      tip.style.top = "6px";
    });
    svg.addEventListener("pointerleave", function () { tip.hidden = true; });
  }

  // ------------------------------------------------------------------ overview
  function renderOverview() {
    var s = D.summary, q = D.quality, share = s.fraud_calls / D.meta.records;
    var el = $("#tab-overview");
    var cards = Object.keys(D.schemes.fraud).map(function (code) {
      var meta = D.schemes.fraud[code], b = s.by_scheme[code];
      var detail = "";
      if (Object.keys(b.roles).length > 1) {
        detail = Object.keys(b.roles).sort().map(function (r) { return b.roles[r] + " " + plural(b.roles[r], ROLE_FORMS[r] || ["", "", ""]); }).join(" и ");
      } else if (GROUP_FORMS[code]) {
        detail = b.groups + " " + plural(b.groups, GROUP_FORMS[code]);
      }
      return '<button class="scheme" type="button" data-go-scheme="' + code + '" style="--c:' + schemeColor(code) + '">' +
        '<span class="scheme-top"><span class="scheme-name"><b>' + esc(meta.title) + "</b><span>" + esc(meta.subtitle) + "</span></span>" +
        '<svg class="picto" viewBox="0 0 76 44" aria-hidden="true">' + PICTO[code] + "</svg></span>" +
        '<span class="scheme-count"><b>' + nf(b.numbers) + "</b><span>" + plural(b.numbers, ["номер", "номера", "номеров"]) +
        (detail ? " · " + esc(detail) : "") + "</span></span>" +
        "<p>" + esc(meta.how) + "</p>" +
        '<span class="scheme-foot"><span><span class="code">' + code + "</span> · " + nf(b.calls) + " " + plural(b.calls, ["вызов", "вызова", "вызовов"]) + '</span><span class="go">Номера →</span></span></button>';
    }).join("");
    cards += '<button class="scheme total" type="button" data-go-scheme="all"><span class="scheme-top"><span class="scheme-name"><b>Файл ответа</b><span>один номер на строку, схема через «;»</span></span></span>' +
      '<span class="scheme-count"><b>' + nf(s.fraud_numbers) + "</b><span>" + plural(s.fraud_numbers, ["номер", "номера", "номеров"]) + " в " + s.fraud_groups + " " + plural(s.fraud_groups, ["группе", "группах", "группах"]) + "</span></span>" +
      "<p>Каждый номер идёт с баллом, списком причин и рекомендацией. Ни один распознанный легальный источник в файл не попал.</p>" +
      '<span class="scheme-foot"><span><span class="code">answer.txt</span></span><span class="go">Все номера →</span></span></button>';
    var traps = Object.keys(D.schemes.legit).map(function (code) {
      var meta = D.schemes.legit[code];
      return '<div class="trap"><div class="trap-top"><b>' + esc(meta.title) + "</b><span>" + nf(s.legit_by_type[code]) + "</span></div>" +
        "<dl><div><dt>Чем похож на фрод</dt><dd>" + esc(meta.looks_like) + "</dd></div><div><dt>Почему не тронули</dt><dd>" + esc(meta.differs) + "</dd></div></dl></div>";
    }).join("");
    el.innerHTML =
      '<div class="hero"><div class="eyebrow">Выгрузка коммутатора · 1–5 октября 2026 · ' + nf(q.files) + " файл" + plural(q.files, ["", "а", "ов"]) + "</div>" +
      '<h1 class="h-display">' + plural(s.fraud_numbers, ["Найден", "Найдено", "Найдено"]) + " " + nf(s.fraud_numbers) + " " + plural(s.fraud_numbers, ["номер", "номера", "номеров"]) + " из семи мошеннических схем</h1>" +
      '<p class="lead">Только по «конверту» вызова: кто, кому, когда и сколько секунд. Содержимое разговоров не используется. ' +
      "<b>" + nf(s.legit_numbers) + " " + plural(s.legit_numbers, ["легальный массовый источник", "легальных массовых источника", "легальных массовых источников"]) + "</b> — колл-центры, банки, диспетчерские — распознаны и в ответ не попали.</p></div>" +
      '<div class="tiles">' +
      tile("Записей обработано", nf(D.meta.records), nf(q.rows_fixed) + " " + plural(q.rows_fixed, ["строка", "строки", "строк"]) + " с ошибками формата исправлено") +
      tile("Номеров в ответе", nf(s.fraud_numbers), "7 схем, детекторы отработали за " + Math.round(D.meta.detect_s || D.meta.runtime_s) + " с") +
      tile("Вызовов с участием схем", nf(s.fraud_calls), pc(share, 1) + " всего трафика") +
      tile("Легальных источников", nf(s.legit_numbers), '<span class="ok">из них в ответе: ' + s.legit_conflicts + "</span>") +
      tile("Автоблокировка допустима", nf(s.autoblock), "для остальных " + nf(s.fraud_numbers - s.autoblock) + " решение за человеком") +
      "</div>" +
      '<div class="panel"><div class="panel-head"><h3>Трафик по часам</h3><div class="seg" role="group" aria-label="Вид">' +
      '<button type="button" data-view="chart" aria-pressed="' + (state.chartView === "chart") + '">График</button>' +
      '<button type="button" data-view="table" aria-pressed="' + (state.chartView === "table") + '">Таблица</button></div></div>' +
      '<div class="panel-body" id="traffic"></div></div>' +
      earlyHTML() +
      '<div class="sec-head"><h2 class="h-sec">Семь схем</h2><p>У каждой свой почерк в метаданных. Нажмите на схему, чтобы увидеть её номера и объяснение по каждому.</p></div>' +
      '<div class="schemes">' + cards + "</div>" +
      '<div class="sec-head"><h2 class="h-sec">Легальные «ловушки»</h2><p>Источники, которые похожи на фрод объёмом или длительностью вызовов. Блокировка любого из них — ошибка с ценой.</p></div>' +
      '<div class="traps">' + traps + "</div>";
    renderTraffic();
  }
  function mins(m) { return m < 1 ? Math.round(m * 60) + " с" : m.toFixed(1).replace(".", ",") + " мин"; }
  function earlyHTML() {
    if (!D.early) return "";
    var item = function (code) {
      var e = D.early[code], meta = D.schemes.fraud[code], fa = e.false_alarms_legit + e.false_alarms_unknown;
      return '<div class="early"><div class="early-top"><span class="sch"><span class="dot" style="--c:' + schemeColor(code) + '"></span><b>' + esc(meta.title) + "</b></span>" +
        '<span class="muted">' + e.detected + " из " + e.numbers + " номеров пойманы</span></div>" +
        '<div class="early-figs"><div><b>' + e.window + '</b><span>вызовов до тревоги</span></div><div><b>' + mins(e.median_minutes) + "</b><span>от первого вызова, медиана</span></div>" +
        "<div><b>" + pc(e.prevented_share) + "</b><span>вызовов схемы после тревоги</span></div><div><b>" + fa + "</b><span>тревог на посторонних номерах</span></div></div>" +
        '<p class="note">Правило: ' + esc(e.rule) + ".</p></div>";
    };
    return '<div class="sec-head"><h2 class="h-sec">Как рано это видно</h2><p>Те же признаки, но скользящим окном по последним вызовам номера — так, как их считал бы обработчик на коммутаторе.</p></div>' +
      '<div class="two">' + item("S1") + item("S2") + "</div>";
  }
  function tile(label, value, note) {
    return '<div class="tile"><div class="label">' + label + '</div><div class="value">' + value + '</div><div class="note">' + note + "</div></div>";
  }
  function renderTraffic() {
    var box = $("#traffic");
    if (!box) return;
    var tot = D.hourly.total, fr = D.hourly.fraud;
    if (state.chartView === "table") {
      var rows = "";
      for (var d = 0; d * 24 < tot.length; d++) {
        var a = tot.slice(d * 24, d * 24 + 24).reduce(function (x, y) { return x + y; }, 0);
        var b = fr.slice(d * 24, d * 24 + 24).reduce(function (x, y) { return x + y; }, 0);
        rows += "<tr><td>" + dayLabel(d * 24) + '</td><td class="num">' + nf(a) + '</td><td class="num">' + nf(b) + '</td><td class="num">' + pc(b / a, 1) + "</td></tr>";
      }
      box.innerHTML = '<div class="scroll-x"><table class="data"><thead><tr><th>День</th><th class="num">Все вызовы</th><th class="num">С участием схем</th><th class="num">Доля</th></tr></thead><tbody>' + rows + "</tbody></table></div>";
      return;
    }
    box.innerHTML =
      '<div class="chart"><div class="chart-title"><i style="--c:var(--accent)"></i>Все вызовы, в час</div><div class="chart-box" id="ch-total"></div></div>' +
      '<div class="chart"><div class="chart-title"><i style="--c:var(--critical)"></i>Вызовы с участием найденных номеров, в час</div><div class="chart-box" id="ch-fraud"></div></div>';
    areaChart($("#ch-total"), tot, { color: "var(--accent)", label: "Все вызовы по часам", unit: "вызовов" });
    areaChart($("#ch-fraud"), fr, { color: "var(--critical)", label: "Вызовы с участием найденных номеров по часам", unit: "вызовов схем", height: 130 });
  }

  // ------------------------------------------------------------------ tables
  function meter(card) {
    return '<span class="meter" style="--sev:' + sevColor(card) + ";--w:" + card.score + '%"><b>' + card.score + "</b><i></i></span>";
  }
  function actCell(card) {
    var d = card.decision;
    return '<span class="act" style="--sev:' + sevColor(card) + '">' + (ICON[d.action] || "") + esc(d.label) + "</span>";
  }
  function schemeCell(card) {
    return '<span class="sch"><span class="dot" style="--c:' + schemeColor(card.scheme) + '"></span>' + esc(schemeMeta(card.scheme).title) + "</span>";
  }
  function match(card, q) {
    if (!q) return true;
    var digits = q.replace(/\D/g, "");
    if (digits && card.number.indexOf(digits.replace(/^[78](?=\d{10}$)/, "")) >= 0) return true;
    var text = (schemeMeta(card.scheme).title + " " + D.schemes.roles[card.role] + " " + card.operator).toLowerCase();
    return !digits && text.indexOf(q.toLowerCase()) >= 0;
  }

  function renderNumbers() {
    var el = $("#tab-numbers"), s = D.summary;
    var chips = '<button class="chip" type="button" data-scheme="all" aria-pressed="' + (state.scheme === "all") + '">Все <b>' + nf(D.numbers.length) + "</b></button>" +
      Object.keys(D.schemes.fraud).map(function (code) {
        return '<button class="chip" type="button" data-scheme="' + code + '" aria-pressed="' + (state.scheme === code) + '"><span class="dot" style="--c:' + schemeColor(code) + '"></span>' +
          esc(D.schemes.fraud[code].title) + " <b>" + s.by_scheme[code].numbers + "</b></button>";
      }).join("");
    var list = D.numbers.filter(function (c) {
      return (state.scheme === "all" || c.scheme === state.scheme) && (state.action === "all" || (state.action === "auto" ? c.decision.autoblock : c.decision.action === state.action)) && match(c, state.q);
    });
    var vol = function (c) { return (c.seen && c.seen.records) || 0; };
    if (state.sort === "volume") list = list.slice().sort(function (x, y) { return vol(y) - vol(x); });
    var rows = list.slice(0, state.limit).map(function (c) {
      return '<tr tabindex="0" data-open="' + c.number + '"><td><span class="n"><span class="mono">' + showNum(c.number) + "</span><small>" + esc(c.operator) + "</small></span></td>" +
        "<td>" + schemeCell(c) + "</td><td>" + esc(D.schemes.roles[c.role]) + '</td><td class="num">' + nf(vol(c)) + "</td><td>" + meter(c) + "</td><td>" + actCell(c) + "</td><td>" + (c.decision.autoblock ? "да" : "нет") + "</td></tr>";
    }).join("");
    el.innerHTML =
      '<div class="sec-head"><h2 class="h-sec">Номера в ответе</h2><p>Каждый номер — с баллом и причинами. Нажмите на строку, чтобы открыть карточку.</p></div>' +
      '<div class="filters"><label class="search">' + ICON.search + '<span class="sr">Поиск</span><input id="q" type="search" placeholder="Номер, схема или оператор" value="' + esc(state.q) + '" autocomplete="off"></label>' +
      '<label><span class="sr">Решение</span><select class="sel" id="f-action">' +
      [["all", "Любое решение"], ["auto", "Автоблокировка: да"], ["block", "Заблокировать"], ["flag", "Пометить абоненту"], ["review", "На проверку"]].map(function (o) {
        return '<option value="' + o[0] + '"' + (state.action === o[0] ? " selected" : "") + ">" + o[1] + "</option>";
      }).join("") + "</select></label>" +
      '<label><span class="sr">Сортировка</span><select class="sel" id="f-sort"><option value="score"' + (state.sort === "score" ? " selected" : "") + '>Сначала высокий балл</option><option value="volume"' + (state.sort === "volume" ? " selected" : "") + ">Сначала больше вызовов</option></select></label></div>" +
      '<div class="chips">' + chips + "</div>" +
      '<div class="panel"><div class="scroll-x"><table class="data"><thead><tr><th>Номер</th><th>Схема</th><th>Роль</th><th class="num">Записей</th><th>Балл</th><th>Рекомендация</th><th>Автоблок</th></tr></thead><tbody class="rows">' +
      (rows || '<tr><td colspan="7"><div class="empty">Ничего не найдено. Измените запрос или сбросьте фильтры.</div></td></tr>') + "</tbody></table></div></div>" +
      '<div class="count-line">Показано ' + Math.min(state.limit, list.length) + " из " + list.length + "</div>" +
      (list.length > state.limit ? '<button class="more" type="button" data-more="numbers">Показать ещё</button>' : "");
  }

  function renderLegit() {
    var el = $("#tab-legit"), s = D.summary;
    var chips = '<button class="chip" type="button" data-legit="all" aria-pressed="' + (state.legitType === "all") + '">Все <b>' + nf(D.legit.length) + "</b></button>" +
      Object.keys(D.schemes.legit).map(function (code) {
        return '<button class="chip" type="button" data-legit="' + code + '" aria-pressed="' + (state.legitType === code) + '">' + esc(D.schemes.legit[code].title) + " <b>" + s.legit_by_type[code] + "</b></button>";
      }).join("");
    var list = D.legit.filter(function (c) { return state.legitType === "all" || c.scheme === state.legitType; });
    list.sort(function (a, b) { return (b.stats.n_out || b.stats.forwards || 0) - (a.stats.n_out || a.stats.forwards || 0); });
    var rows = list.slice(0, state.legitLimit).map(function (c) {
      var vol = c.stats.n_out != null ? nf(c.stats.n_out) + " исх." : nf(c.stats.forwards || 0) + " переадр.";
      var why = c.factors.filter(function (f) { return f.points < 0; }).map(function (f) { return f.label; })[0] || "";
      return '<tr tabindex="0" data-open="' + c.number + '"><td><span class="n"><span class="mono">' + showNum(c.number) + "</span><small>" + esc(c.operator) + "</small></span></td>" +
        "<td>" + schemeCell(c) + '</td><td class="num">' + vol + "</td><td>" + meter(c) + "</td><td>" + esc(why) + "</td></tr>";
    }).join("");
    el.innerHTML =
      '<div class="sec-head"><h2 class="h-sec">Похожи на фрод, но не фрод</h2><p>Система не просто молчит об этих номерах: она объясняет, какой признак настораживает и какой снимает подозрение.</p></div>' +
      '<div class="chips">' + chips + "</div>" +
      '<div class="panel"><div class="scroll-x"><table class="data"><thead><tr><th>Номер</th><th>Тип источника</th><th class="num">Объём</th><th>Балл</th><th>Главный довод «за»</th></tr></thead><tbody class="rows">' + rows + "</tbody></table></div></div>" +
      '<div class="count-line">Показано ' + Math.min(state.legitLimit, list.length) + " из " + list.length + "</div>" +
      (list.length > state.legitLimit ? '<button class="more" type="button" data-more="legit">Показать ещё</button>' : "");
  }

  // ------------------------------------------------------------------ envelope card
  function factorsHTML(factors) {
    return factors.map(function (f) {
      var trust = f.points < 0, mag = Math.abs(f.points);
      var color = trust ? "var(--good)" : mag >= 30 ? "var(--critical)" : mag >= 15 ? "var(--serious)" : "var(--warning)";
      return '<div class="fact' + (trust ? " trust" : "") + '" style="--fc:' + color + ";--w:" + Math.min(100, mag * 2) + '%"><span class="t">' + esc(f.label) +
        '</span><span class="p">' + (f.points > 0 ? "+" : f.points < 0 ? "−" : "") + mag + '</span><span class="barline"></span></div>';
    }).join("");
  }
  function verdictHTML(dec) {
    var rec = dec.recommendation || dec.label;
    return '<div class="verdict"><span class="pill">' + (ICON[dec.action] || "") + "рекомендация: " + esc(rec.charAt(0).toLowerCase() + rec.slice(1)) + "</span>" +
      '<span class="pill ' + (dec.autoblock ? "bad" : "ok") + '">' + (dec.autoblock ? ICON.block : ICON.allow) + "автоблокировка: " + (dec.autoblock ? "да" : "нет") + "</span></div>" +
      '<p class="why">' + esc(dec.reason) + "</p>";
  }
  function stampHTML(score, color, light, caption) {
    return '<div class="stamp' + (light ? " light" : "") + '" style="--sev:' + color + '"><b>' + score + "</b><span>" + caption + "</span></div>";
  }

  function mlLine(c) {
    if (!D.ml) return "";
    var text;
    if (c.ml_prob == null) text = "Модель по профилю здесь не применяется: номер сам почти не звонит, его выдаёт только граф связей.";
    else {
      var agree = isLegit(c) ? c.ml_prob < D.ml.threshold : c.ml_prob >= D.ml.threshold;
      text = "Вероятность фрода по модели — <b>" + pc(c.ml_prob) + "</b>. " + (agree ? (isLegit(c) ? "Модель тоже не считает номер мошенническим." : "Модель согласна с детектором.") : "Модель расходится с детектором — стоит проверить вручную.");
    }
    return '<div class="env-sec second"><h4>Второе мнение · CatBoost</h4><p class="note">' + text + "</p></div>";
  }

  function numberCardHTML(c) {
    var meta = schemeMeta(c.scheme), st = c.stats || {}, legit = isLegit(c);
    var seen = c.seen || {};
    var env =
      '<div class="env"><div class="env-edge"></div><div class="env-head"><div class="env-addr">' +
      '<div class="addr"><span class="k">Номер</span><span class="v">' + showNum(c.number) + '</span><span class="s"><span>' + esc(c.operator) + "</span>" + schemeCell(c) + "<span>" + esc(D.schemes.roles[c.role]) + "</span></span></div>" +
      '<div class="postmark">' + ICON.postmark + "<span>" + nf(seen.records || 0) + " " + plural(seen.records || 0, ["запись", "записи", "записей"]) + " в выгрузке · " + ts(seen.first) + " → " + ts(seen.last) + "</span></div></div>" +
      stampHTML(c.score, sevColor(c), sevLight(c), "балл") + "</div>" +
      '<div class="env-sec"><h4>' + (legit ? "Что настораживает и что снимает подозрение" : "Что дало этот балл") + "</h4>" + factorsHTML(c.factors) + "</div>" +
      '<div class="env-sec">' + verdictHTML(c.decision) + "</div>" + mlLine(c) + "</div>";

    var kv = [];
    if (st.n_out != null) kv.push(["Исходящих", nf(st.n_out)]);
    if (st.uniq_b != null) kv.push(["Разных собеседников", nf(st.uniq_b)]);
    if (st.n_in != null) kv.push(["Входящих", nf(st.n_in)]);
    if (st.median_dur != null) kv.push(["Медиана длительности", Math.round(st.median_dur) + " с"]);
    if (st.zero_share != null) kv.push(["Без ответа", pc(st.zero_share)]);
    if (st.night_share != null) kv.push(["Ночью (22–06)", pc(st.night_share)]);
    if (st.n_imsi > 1) kv.push(["SIM-карт (IMSI)", st.n_imsi]);
    if (st.forwards != null) kv.push(["Переадресаций", nf(st.forwards)]);
    if (st.chains != null) kv.push(["Вызовов через цепочку", nf(st.chains)]);
    var html = env;
    html += '<div class="block"><h4>Как работает схема</h4><p class="note">' + esc(meta.how || (meta.looks_like + ". " + meta.differs + ".")) + "</p></div>";
    if (kv.length) html += '<div class="block"><h4>Профиль за 5 дней</h4><dl class="kv">' + kv.map(function (p) { return "<div><dt>" + p[0] + "</dt><dd>" + p[1] + "</dd></div>"; }).join("") + "</dl></div>";
    if (c.activity && c.activity.some(function (v) { return v > 0; })) html += '<div class="block"><h4>Исходящие по часам</h4><div class="chart-box" id="act-chart"></div></div>';
    var g = c.group && D.groups[c.group];
    if (g && g.members.length >= 3 && g.edges.length) html += '<div class="block"><h4>Связи в группе</h4><div class="graph" id="graph"></div></div>';
    if (c.related && c.related.length) {
      html += '<div class="block"><h4>Связанные номера · ' + c.related.length + '</h4><div class="rel">' + c.related.slice(0, 40).map(function (n) {
        return IDX[n] ? '<button type="button" data-open="' + n + '">' + showNum(n) + "</button>" : '<button type="button" disabled>' + showNum(n) + "</button>";
      }).join("") + "</div></div>";
    }
    if (c.samples && c.samples.length) {
      html += '<div class="block"><h4>Конверты вызовов (примеры)</h4><div class="cdr">' + c.samples.map(function (r) {
        var me = function (n) { return n === c.number ? "<b>" + rawNum(n) + "</b>" : rawNum(n); };
        return r.type + "  " + me(r.a) + " → " + me(r.b) + (r.c ? " → " + me(r.c) : "") + "   " + r.ts.slice(5, 16) + "   " + (r.dur == null ? "—" : r.dur + " с");
      }).join("\n") + "</div></div>";
    }
    return html;
  }

  function drawGraph(box, c) {
    var g = D.groups[c.group], color = schemeColor(c.scheme), W = Math.max(260, box.clientWidth);
    var nodes = g.members.slice(), pos = {}, svg = "", H;
    if (g.scheme === "S5") {
      var path = c.stats.path, uniq = path.filter(function (n, i) { return path.indexOf(n) === i; });
      var ring = path.length > uniq.length, step = (W - 60) / Math.max(1, uniq.length - 1);
      H = ring ? 110 : 70;
      uniq.forEach(function (n, i) { pos[n] = [30 + i * step, 28]; });
      for (var i = 0; i < uniq.length - 1; i++) svg += '<line class="edge" stroke-width="2" x1="' + (pos[uniq[i]][0] + 9) + '" y1="28" x2="' + (pos[uniq[i + 1]][0] - 12) + '" y2="28" marker-end="url(#arr)"/>';
      if (ring) svg += '<path class="edge" fill="none" stroke-width="2" d="M' + pos[uniq[uniq.length - 1]][0] + " 38V70a8 8 0 01-8 8H38a8 8 0 01-8-8V42" + '" marker-end="url(#arr)"/><text x="' + (W / 2) + '" y="98" text-anchor="middle">кольцо: вызов возвращается в начало, длительность 0</text>';
      nodes = uniq;
    } else {
      H = Math.min(300, W * 0.62);
      var cx = W / 2, cy = H / 2, R = Math.min(cx, cy) - 30;
      var hub = (g.scheme === "S1" || g.scheme === "S7") ? g.edges[0] && g.edges[0][0] : null;
      var ringNodes = nodes.filter(function (n) { return n !== hub; });
      ringNodes.forEach(function (n, i) { var a = -Math.PI / 2 + i * 2 * Math.PI / ringNodes.length; pos[n] = [cx + R * Math.cos(a), cy + R * Math.sin(a)]; });
      if (hub) pos[hub] = [cx, cy];
      var maxW = Math.max.apply(null, g.edges.map(function (e) { return e[2]; }));
      g.edges.forEach(function (e) {
        if (!pos[e[0]] || !pos[e[1]]) return;
        svg += '<line class="edge" x1="' + pos[e[0]][0] + '" y1="' + pos[e[0]][1] + '" x2="' + pos[e[1]][0] + '" y2="' + pos[e[1]][1] + '" stroke-width="' + (1 + 3 * e[2] / maxW).toFixed(1) + '" opacity="0.7"><title>' + e[2] + " вызовов</title></line>";
      });
    }
    nodes.forEach(function (n) {
      if (!pos[n]) return;
      var below = pos[n][1] > H / 2 || g.scheme === "S5";
      svg += '<circle class="node' + (n === c.number ? " me" : "") + '" data-open="' + n + '" cx="' + pos[n][0] + '" cy="' + pos[n][1] + '" r="8" style="--c:' + color + '"><title>' + showNum(n) + "</title></circle>" +
        '<text x="' + pos[n][0] + '" y="' + (pos[n][1] + (below ? 22 : -13)) + '" text-anchor="middle">…' + n.slice(-4) + "</text>";
    });
    box.innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Связи между номерами группы"><defs><marker id="arr" viewBox="0 0 8 8" refX="6" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0l8 4-8 4z" style="fill:var(--line-strong)"/></marker></defs>' + svg + "</svg>";
  }

  function openCard(num) {
    var c = IDX[num];
    if (!c) return;
    state.selected = num;
    var root = $("#drawer-root");
    root.innerHTML = '<div class="scrim" data-close></div><aside class="drawer" role="dialog" aria-modal="true" aria-label="Карточка номера">' +
      '<div class="drawer-top"><span class="eyebrow">Карточка номера</span><button class="x" type="button" data-close aria-label="Закрыть">' + ICON.x + "</button></div>" + numberCardHTML(c) + "</aside>";
    var act = $("#act-chart", root);
    if (act) columnChart(act, c.activity, schemeColor(c.scheme));
    var gr = $("#graph", root);
    if (gr) drawGraph(gr, c);
    $(".x", root).focus();
    document.documentElement.style.overflow = "hidden";
  }
  function closeCard() {
    state.selected = null;
    $("#drawer-root").innerHTML = "";
    document.documentElement.style.overflow = "";
  }

  // ------------------------------------------------------------------ call check
  var TYPES = { "01": "входящий", "02": "исходящий", "03": "переадресация" };
  function scoreCall(call) {
    var A = IDX[call.a], B = IDX[call.b], Cc = call.c ? IDX[call.c] : null;
    var res = { score: 0, factors: [], notes: [], decision: null, color: "var(--good)", light: false };
    var fraud = function (c) { return c && !isLegit(c); };
    if (EMERGENCY[call.b] || EMERGENCY[call.a]) {
      var who = EMERGENCY[call.b] ? "Вызов на номер " + call.b + " (" + EMERGENCY[call.b] + ")" : "Вызов от службы " + call.a + " (" + EMERGENCY[call.a] + ")";
      res.score = fraud(A) ? A.score : 0;
      res.color = "var(--good)";
      res.factors = fraud(A) ? A.factors : [];
      res.notes.push(who + " пропускается до любого скоринга.");
      if (fraud(A)) res.notes.push("Звонящий номер под подозрением (" + schemeMeta(A.scheme).title + ", балл " + A.score + "), но человек с заблокированного номера тоже может вызывать скорую. Балл показан для сведения и на решение не влияет.");
      res.decision = { action: "never_block", label: "Никогда не блокировать", recommendation: "Пропустить без условий", autoblock: false, reason: "Экстренные и социально значимые номера в белом списке: цена ошибки — человеческая жизнь" };
      return res;
    }
    var main = null, why = "";
    if (fraud(A)) { main = A; why = "звонящий номер"; }
    if (fraud(B) && (!main || B.score > main.score)) { main = B; why = "номер, на который звонят"; }
    if (fraud(Cc) && (!main || Cc.score > main.score)) { main = Cc; why = "номер переадресации"; }
    if (main) {
      res.score = main.score; res.factors = main.factors; res.color = sevColor(main); res.light = sevLight(main);
      res.notes.push("Балл определяет " + why + ": " + schemeMeta(main.scheme).title + ", роль — " + D.schemes.roles[main.role].toLowerCase() + ".");
      if (main === A) {
        res.decision = main.decision;
        if (main.scheme === "S1" && call.dur != null && call.dur <= 2) res.notes.push("Этот вызов — сброс на " + call.dur + "-й секунде, типичный для схемы.");
      } else {
        res.notes.push("Абонент сам звонит на номер схемы — скорее всего, перезванивает после сброса.");
        res.decision = { action: "flag", label: "Предупредить абонента", recommendation: "Предупредить звонящего до соединения: «Номер связан с мошенничеством»", autoblock: false, reason: "Звонящий — вероятная жертва, блокировать его нельзя; опасен номер назначения" };
      }
      return res;
    }
    var known = A || B;
    if (known) {
      res.score = known.score; res.factors = known.factors; res.color = "var(--good)";
      res.notes.push((known === A ? "Звонящий" : "Вызываемый") + " номер распознан как легитимный массовый источник: " + schemeMeta(known.scheme).title.toLowerCase() + ".");
      res.decision = known.decision;
      return res;
    }
    res.notes.push("Ни один из номеров не входит в найденные схемы и не является массовым источником.");
    res.decision = { action: "allow", label: "Пропускать", recommendation: "Пропустить", autoblock: false, reason: "Признаков мошенничества нет" };
    return res;
  }

  function callCardHTML(call) {
    var r = scoreCall(call);
    var line = function (k, num) {
      var c = IDX[num];
      return '<div class="addr"><span class="k">' + k + '</span><span class="v">' + (EMERGENCY[num] ? num : showNum(num)) + '</span><span class="s"><span>' + esc(operator(num)) + "</span>" +
        (c ? schemeCell(c) + "<span>" + esc(D.schemes.roles[c.role]) + "</span>" : "") + "</span></div>";
    };
    return '<div class="env"><div class="env-edge"></div><div class="env-head"><div class="env-addr">' + line("От", call.a) + line("Кому", call.b) + (call.c ? line("Далее", call.c) : "") +
      '<div class="postmark">' + ICON.postmark + "<span>" + TYPES[call.type] + " · " + (call.dur == null || call.dur === "" ? "длительность неизвестна" : call.dur + " с") + (call.ts ? " · " + ts(call.ts) : "") + "</span></div></div>" +
      stampHTML(r.score, r.color, r.light, "риск") + "</div>" +
      (r.factors.length ? '<div class="env-sec"><h4>Что дало этот балл</h4>' + factorsHTML(r.factors) + "</div>" : "") +
      '<div class="env-sec">' + r.notes.map(function (n) { return '<p class="note">' + esc(n) + "</p>"; }).join("") + "</div>" +
      '<div class="env-sec">' + verdictHTML(r.decision) + "</div></div>";
  }

  var PRESETS = [];
  function buildPresets() {
    var pick = function (scheme, role, test) {
      for (var i = 0; i < D.numbers.length + D.legit.length; i++) {
        var c = i < D.numbers.length ? D.numbers[i] : D.legit[i - D.numbers.length];
        if (c.scheme !== scheme || (role && c.role !== role)) continue;
        for (var j = 0; j < c.samples.length; j++) if (!test || test(c.samples[j], c)) return c.samples[j];
      }
      return null;
    };
    var add = function (title, sub, s) { if (s) PRESETS.push({ title: title, sub: sub, call: { type: s.type, a: s.a, b: s.b, c: s.c || "", dur: s.dur, ts: s.ts } }); };
    add("Wangiri: звонок-сброс", "Номер-приманка сбрасывает на первой секунде", pick("S1", "initiator", function (s, c) { return s.a === c.number && s.type === "02"; }));
    add("Жертва перезванивает", "Перезвон уходит на платный номер", pick("S1", "premium", function (s) { return s.type === "03"; }));
    add("Робот перебирает номера", "Очередной номер из диапазона подряд", pick("S2", "initiator", function (s, c) { return s.a === c.number; }));
    add("Мошенник звонит жертве", "Длинный разговор после «прогрева»", pick("S7", "fraudster", function (s, c) { return s.a === c.number; }));
    add("Вызов через цепочку", "Переадресация B → C → D", pick("S5", "node", function (s) { return s.type === "03"; }));
    add("Банк оповещает клиента", "Массовый, короткий — и легальный", pick("D2", null, function (s, c) { return s.a === c.number; }));
    var sim = D.numbers.filter(function (c) { return c.scheme === "S3"; })[0];
    if (sim) PRESETS.push({ title: "SIM из шлюза звонит в 103", sub: "Что будет, если заблокировать скорую?", call: { type: "02", a: sim.number, b: "103", c: "", dur: 95, ts: "" } });
    PRESETS.push({ title: "Обычный звонок", sub: "Два абонента, которых нет в схемах", call: { type: "02", a: "8991234567", b: "0261234567", c: "", dur: 54, ts: "" } });
  }
  var currentCall = null;
  function renderCheck() {
    var el = $("#tab-check");
    if (!currentCall) currentCall = PRESETS[0].call;
    var c = currentCall;
    el.innerHTML =
      '<div class="sec-head"><h2 class="h-sec">Проверка одного вызова</h2><p>Так ответ системы выглядит для оператора в момент вызова: балл, причины, рекомендация и отдельное решение об автоблокировке.</p></div>' +
      '<div class="check"><form class="form" id="call-form" autocomplete="off">' +
      '<div class="field"><label for="c-a">Номер A — кто звонит</label><input id="c-a" value="' + esc(c.a) + '" inputmode="numeric" maxlength="12"></div>' +
      '<div class="field"><label for="c-b">Номер B — кому</label><input id="c-b" value="' + esc(c.b) + '" inputmode="numeric" maxlength="12"></div>' +
      '<div class="row2"><div class="field"><label for="c-type">Тип</label><select id="c-type">' + Object.keys(TYPES).map(function (t) { return '<option value="' + t + '"' + (c.type === t ? " selected" : "") + ">" + t + " — " + TYPES[t] + "</option>"; }).join("") + "</select></div>" +
      '<div class="field"><label for="c-dur">Длительность, с</label><input id="c-dur" value="' + esc(c.dur == null ? "" : c.dur) + '" inputmode="numeric" maxlength="6"></div></div>' +
      '<div class="field"><label for="c-c">Номер C — куда переадресован (если тип 03)</label><input id="c-c" value="' + esc(c.c || "") + '" inputmode="numeric" maxlength="12"></div>' +
      '<button class="more" type="submit" style="justify-self:start">Оценить вызов</button>' +
      '<div class="block"><h4>Готовые примеры из выгрузки</h4><div class="presets">' + PRESETS.map(function (p, i) {
        return '<button class="preset" type="button" data-preset="' + i + '"><b>' + esc(p.title) + "</b><span>" + esc(p.sub) + "</span></button>";
      }).join("") + "</div></div></form>" +
      '<div id="call-result">' + callCardHTML(c) + "</div></div>";
  }
  function readCall() {
    var norm = function (v) { v = v.replace(/\D/g, ""); return v.length === 11 && /^[78]/.test(v) ? v.slice(1) : v; };
    var dur = $("#c-dur").value.trim();
    return { type: $("#c-type").value, a: norm($("#c-a").value), b: norm($("#c-b").value), c: norm($("#c-c").value), dur: dur === "" || isNaN(+dur) ? null : Math.max(0, Math.round(+dur)), ts: "" };
  }

  // ------------------------------------------------------------------ method
  function renderMethod() {
    var el = $("#tab-method"), q = D.quality, s = D.summary, t = D.thresholds;
    var issues = q.issues.map(function (i) {
      return "<tr><td>" + esc(i.title) + '</td><td class="num">' + nf(i.count) + '</td><td class="mono" style="font-size:12px;color:var(--ink-2)">' + esc(i.examples[0] || "") + "</td></tr>";
    }).join("");
    var tier = function (icon, color, title, text) { return '<div class="tier" style="--sev:' + color + '">' + ICON[icon] + "<b>" + title + "</b><p>" + text + "</p></div>"; };
    el.innerHTML =
      '<div class="sec-head"><h2 class="h-sec">От сырой выгрузки до решения</h2><p>Четыре шага, каждый можно проверить руками. Никакого «чёрного ящика»: балл — это сумма причин.</p></div>' +
      '<div class="steps">' +
      '<div class="step"><b>Чтение и починка</b><p>Лишние поля, коды страны, несуществующие даты, «abc» вместо секунд, испорченный код оператора. Каждая правка учтена, ничего не теряется молча.</p><span class="fig">' + nf(q.rows) + " строк · " + nf(q.rows_fixed) + " исправлено</span></div>" +
      '<div class="step"><b>Профиль номера</b><p>По каждому номеру за окно: сколько вызовов, кому, когда, сколько длятся, сколько без ответа, есть ли входящие, сколько SIM.</p><span class="fig">' + nf(D.meta.numbers_seen) + " номеров</span></div>" +
      '<div class="step"><b>Детекторы схем</b><p>Семь детекторов ищут почерк схемы: в статистике номера и в графе связей (группы, цепочки, кольца). Пять распознавателей узнают легальные источники.</p><span class="fig">7 схем · 5 легальных профилей</span></div>' +
      '<div class="step"><b>Балл и решение</b><p>Каждый фактор даёт очки, сумма — балл 0–100. Рекомендация и автоблокировка считаются отдельно, по политике ниже.</p><span class="fig">' + nf(s.fraud_numbers) + " в ответе · " + nf(s.autoblock) + " к автоблокировке</span></div></div>" +
      '<div class="two"><div class="panel"><div class="panel-head"><h3>Политика реагирования</h3></div><div class="panel-body" style="gap:0">' +
      tier("block", "var(--critical)", "Заблокировать автоматически", "Балл от " + t.AUTOBLOCK_MIN_SCORE + ", минимум три независимых фактора и схема, у которой нет легального применения: Wangiri, робот, SIM-box, клон SIM.") +
      tier("flag", "var(--serious)", "Пометить абоненту", "Балл от 75. Абонент видит «Возможно мошенник». Блокировать ли — решает человек: для вишинга, цепочек и каруселей цена ошибки выше.") +
      tier("review", "var(--warning)", "На проверку аналитику", "Балл " + t.ANSWER_MIN_SCORE + "–74 или номер похож сразу и на фрод, и на легальный профиль.") +
      tier("allow", "var(--good)", "Пропускать", "Распознан легальный массовый источник либо признаков нет.") +
      "</div></div>" +
      '<div class="panel"><div class="panel-head"><h3>Что будет, если система заблокирует скорую?</h3></div><div class="panel-body">' +
      '<p class="note">Не заблокирует. Вызов на экстренный номер пропускается до любого скоринга, даже если звонящий уже в чёрном списке: человек с заблокированной SIM тоже может вызывать помощь.</p>' +
      '<div class="sos">' + Object.keys(EMERGENCY).map(function (n) { return "<span>" + n + "</span>"; }).join("") + "</div>" +
      '<p class="note">Вызовы от экстренных служб и номеров из белого списка оператора (банки, госуслуги, горячие линии) автоматически не блокируются никогда. Автоблокировка остальных — это ' + nf(s.autoblock) + " из " + nf(s.fraud_numbers) + " номеров; по остальным система только советует.</p>" +
      '<button class="more" type="button" data-tabgo="check" style="justify-self:start">Проверить на примере</button></div></div></div>' +
      mlPanel() +
      '<div class="panel"><div class="panel-head"><h3>Качество данных: что исправлено при чтении</h3></div><div class="panel-body"><div class="scroll-x"><table class="data"><thead><tr><th>Что не так</th><th class="num">Строк</th><th>Пример исходной строки</th></tr></thead><tbody>' + issues + "</tbody></table></div></div></div>" +
      '<div class="panel"><div class="panel-head"><h3>Честно об ограничениях</h3></div><div class="panel-body">' +
      '<p class="note">В CDR нет IMEI и соты, поэтому SIM-карты шлюзов оцениваются по одной и не раскладываются по конкретным устройствам. В боевой сети это добавляется одним полем.</p>' +
      '<p class="note">Балл здесь считается по окну в пять дней. Для двух самых массовых схем те же признаки проверены и скользящим окном: Wangiri виден через ' + D.early.S1.window + " вызовов, робот — через " + D.early.S2.window + ", без ложных тревог. Остальным схемам нужна история: шлюз и карусель отличаются от обычного абонента только на длинной дистанции.</p>" +
      '<p class="note">Пороги детекторов вынесены в один файл настроек и видны оператору. Разметки в данных нет, поэтому точность проверялась обратным способом: ни один из ' + nf(s.legit_numbers) + " распознанных легальных источников не попал в ответ.</p></div></div>";
  }

  function mlPanel() {
    var m = D.ml;
    if (!m) return "";
    var top = m.importance.slice(0, 8), max = top[0].share;
    var bars = top.map(function (f) {
      return '<div class="hbar"><span class="t">' + esc(f.feature) + '</span><span class="b"><i style="width:' + (100 * f.share / max).toFixed(1) + '%"></i></span><span class="v">' + pc(f.share) + "</span></div>";
    }).join("");
    var unseen = m.unseen.map(function (u) {
      var meta = D.schemes.fraud[u.scheme], share = u.caught / u.numbers;
      return '<tr><td><span class="sch"><span class="dot" style="--c:' + schemeColor(u.scheme) + '"></span>' + esc(meta.title) + '</span></td><td class="num">' + u.numbers + '</td><td class="num">' + u.caught + "</td><td>" +
        '<span class="meter" style="--sev:var(--accent);--w:' + (100 * share).toFixed(0) + '%"><b style="width:38px">' + pc(share) + "</b><i></i></span></td></tr>";
    }).join("");
    return '<div class="panel"><div class="panel-head"><h3>Второй контур: модель перепроверяет детекторы</h3></div><div class="panel-body">' +
      '<p class="note">Разметки в данных нет, поэтому CatBoost учится на находках детекторов, но видит только общий профиль номера: без графа связей и без правил схем. Проверка честная: все номера одной связки или карусели попадают либо в обучение, либо в проверку.</p>' +
      '<div class="early-figs"><div><b>' + nf(m.evaluated) + "</b><span>номеров оценено (от " + m.min_calls + " исходящих)</span></div>" +
      "<div><b>" + m.agree + " из " + m.positives + "</b><span>находок детекторов подтверждены моделью</span></div>" +
      "<div><b>" + (m.rules_only + m.model_only) + "</b><span>расхождений между контурами</span></div>" +
      "<div><b>" + m.legit_flagged + "</b><span>легальных источников модель сочла фродом</span></div></div>" +
      '<div class="two"><div class="block"><h4>Что если схема новая</h4><p class="note">Одну схему целиком убираем из обучения и смотрим, узнает ли её модель.</p>' +
      '<div class="scroll-x"><table class="data"><thead><tr><th>Скрытая схема</th><th class="num">Номеров</th><th class="num">Узнано</th><th>Доля</th></tr></thead><tbody>' + unseen + "</tbody></table></div>" +
      '<p class="note">«Взрывные» схемы модель узнаёт без подсказки. Карусель и вишинг по профилю выглядят как обычный абонент, поэтому для них и нужны детекторы по графу связей.</p></div>' +
      '<div class="block"><h4>На что смотрит модель</h4>' + bars + '<p class="note">Доля вклада признака в решения модели. Главное — как долго живёт номер и звонят ли ему в ответ.</p></div></div></div></div>';
  }

  // ------------------------------------------------------------------ routing + events
  var RENDER = { overview: renderOverview, numbers: renderNumbers, legit: renderLegit, check: renderCheck, method: renderMethod };
  function setTab(tab, push) {
    if (!RENDER[tab]) tab = "overview";
    state.tab = tab;
    $$(".tab").forEach(function (b) { b.setAttribute("aria-selected", String(b.dataset.tab === tab)); });
    $$("main > section").forEach(function (s) { s.hidden = s.id !== "tab-" + tab; });
    RENDER[tab]();
    if (push !== false) { try { history.replaceState(null, "", "#" + tab); } catch (e) { /* в песочнице адрес может быть недоступен */ } }
    window.scrollTo(0, 0);
  }
  function rerender() { RENDER[state.tab](); if (state.selected) openCard(state.selected); }

  document.addEventListener("click", function (ev) {
    var t = ev.target.closest("[data-tab],[data-go-scheme],[data-scheme],[data-legit],[data-open],[data-close],[data-more],[data-view],[data-preset],[data-tabgo]");
    if (!t) return;
    if (t.dataset.tab) setTab(t.dataset.tab);
    else if (t.dataset.tabgo) setTab(t.dataset.tabgo);
    else if (t.dataset.goScheme) { state.scheme = t.dataset.goScheme; state.q = ""; state.action = "all"; state.limit = 50; setTab("numbers"); }
    else if (t.dataset.scheme) { state.scheme = t.dataset.scheme; state.limit = 50; renderNumbers(); }
    else if (t.dataset.legit) { state.legitType = t.dataset.legit; state.legitLimit = 50; renderLegit(); }
    else if (t.dataset.open) openCard(t.dataset.open);
    else if (t.hasAttribute("data-close")) closeCard();
    else if (t.dataset.more === "numbers") { state.limit += 100; renderNumbers(); }
    else if (t.dataset.more === "legit") { state.legitLimit += 100; renderLegit(); }
    else if (t.dataset.view) { state.chartView = t.dataset.view; renderOverview(); }
    else if (t.dataset.preset) { currentCall = PRESETS[+t.dataset.preset].call; renderCheck(); }
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && state.selected) closeCard();
    if (ev.key === "Enter" && ev.target.matches && ev.target.matches("tr[data-open]")) openCard(ev.target.dataset.open);
  });
  document.addEventListener("input", function (ev) {
    if (ev.target.id === "q") {
      state.q = ev.target.value; state.limit = 50;
      var pos = ev.target.selectionStart;
      renderNumbers();
      var q = $("#q"); q.focus(); try { q.setSelectionRange(pos, pos); } catch (e) { /* type=search в части браузеров не даёт ставить курсор */ }
    }
  });
  document.addEventListener("change", function (ev) {
    if (ev.target.id === "f-action") { state.action = ev.target.value; state.limit = 50; renderNumbers(); }
    if (ev.target.id === "f-sort") { state.sort = ev.target.value; state.limit = 50; renderNumbers(); }
  });
  document.addEventListener("submit", function (ev) {
    if (ev.target.id !== "call-form") return;
    ev.preventDefault();
    currentCall = readCall();
    $("#call-result").innerHTML = callCardHTML(currentCall);
  });
  $("#mask-toggle").addEventListener("click", function () {
    state.mask = !state.mask;
    this.setAttribute("aria-pressed", String(state.mask));
    $("#mask-label").textContent = state.mask ? "Номера скрыты" : "Номера открыты";
    store("konvert-mask", state.mask ? "1" : "0");
    rerender();
  });
  $("#theme-toggle").addEventListener("click", function () {
    var root = document.documentElement;
    var cur = root.getAttribute("data-theme") || (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    var next = cur === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    store("konvert-theme", next);
  });
  var resizeTimer;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () { if (state.tab === "overview") renderTraffic(); }, 150);
  });
  // адрес вида #n-8991234567 открывает карточку номера — удобно для ссылок и QR
  function route(h) {
    var m = /^n-(\d{10})$/.exec(h);
    if (m && IDX[m[1]]) { setTab(isLegit(IDX[m[1]]) ? "legit" : "numbers", false); openCard(m[1]); return; }
    setTab(RENDER[h] ? h : "overview", false);
  }
  window.addEventListener("hashchange", function () { var h = location.hash.slice(1); if (h !== state.tab) route(h); });

  // ------------------------------------------------------------------ boot
  function boot(data) {
    D = data;
    D.numbers.forEach(function (c) { IDX[c.number] = c; });
    D.legit.forEach(function (c) { if (!IDX[c.number]) IDX[c.number] = c; });
    if (store("konvert-mask") === "0") { state.mask = false; $("#mask-toggle").setAttribute("aria-pressed", "false"); $("#mask-label").textContent = "Номера открыты"; }
    var th = store("konvert-theme");
    if (th === "dark" || th === "light") document.documentElement.setAttribute("data-theme", th);
    buildPresets();
    route(location.hash.slice(1));
  }
  function fail(err) {
    $("#tab-overview").innerHTML = '<div class="empty">Не удалось загрузить результаты расчёта. Запустите <span class="mono">python -m konvert.pipeline</span> и обновите страницу.<br><small>' + esc(err) + "</small></div>";
  }
  if (window.__KONVERT__) boot(window.__KONVERT__);
  else fetch(window.__KONVERT_URL__ || "results.json").then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }).then(boot).catch(fail);
})();
