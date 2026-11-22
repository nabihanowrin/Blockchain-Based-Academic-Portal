/*
  The EEE loading screen: the logo, the arcs and the title, played whenever
  someone moves between the homepage and an account page (Nabiha's design).

  Every page loads this one file (<script src="loader.js">), so the screen
  looks and moves the same everywhere. It plays:
    - on the homepage, after signing in, before the account page opens
    - on an account page that was opened in a new tab (its address ends in #intro)
    - on an account page, when signing out, before the homepage opens

  Use: eeeLoader(fn) plays it, then runs fn (usually: go to the next page).
*/
(() => {
  // the title font, the look, and the screen itself, added to whichever page loaded this file
  if (!document.querySelector('link[href*="family=Montserrat"]')) {
    const font = document.createElement('link');
    font.rel = 'stylesheet';
    font.href = 'https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700&display=swap';
    document.head.appendChild(font);
  }
  const style = document.createElement('style');
  style.textContent = "\n/* Loading screen shown after a successful sign-in: the logo, then the account page opens. */\n#eee-intro{\n  --ii-cream:#F6F2EE;\n  --ii-centre:#FBF9F7;\n  --ii-grid:rgba(10,30,52,.08);\n  --ii-arc:#BF000A;\n  --ii-navy:#0A1E34;\n  --ii-wave:#7E2233;\n  --ii-title:'Montserrat', 'Arial', sans-serif;\n}\n\n#eee-intro{\n  position:fixed;inset:0;z-index:9999;cursor:pointer;\n  display:none;flex-direction:column;align-items:center;justify-content:center;gap:3vh;\n  padding-block:24px;\n  padding-left:max(16px, env(safe-area-inset-left, 0px));\n  padding-right:max(16px, env(safe-area-inset-right, 0px));\n  background:radial-gradient(60% 55% at 50% 42%, var(--ii-centre) 0%, var(--ii-cream) 75%);\n  overflow:hidden;\n}\n/* faint graph paper */\n#eee-intro.play{display:flex;animation:eeeIn .5s ease both}\n@keyframes eeeIn{from{opacity:0}}\n@media (prefers-reduced-motion:reduce){#eee-intro.play{animation:none}}\n#eee-intro::before{\n  content:\"\";position:absolute;inset:-48px;pointer-events:none;\n  background-image:\n    linear-gradient(var(--ii-grid) 1px, transparent 1px),\n    linear-gradient(90deg, var(--ii-grid) 1px, transparent 1px);\n  background-size:48px 48px;\n  animation:eeeDrift 14s linear infinite;\n}\n@keyframes eeeDrift{to{transform:translate(48px,48px)}}\n\n#eee-logo{width:min(760px, 94vw);max-height:60vh;height:auto;overflow:visible;position:relative}\n.eee-arcs path{fill:none;stroke:var(--ii-arc);opacity:0}\n.eee-scroll{animation:eeeScroll 1.6s linear infinite}\n@keyframes eeeScroll{to{transform:translateX(var(--p))}}\n\n#eee-title{width:min(1150px, 100%);height:auto;overflow:visible;position:relative;display:block}\n.eee-uni{\n  position:relative;font-family:var(--ii-title);font-weight:600;color:var(--ii-navy);\n  font-size:clamp(15px, 2vw, 24px);letter-spacing:.22em;text-transform:uppercase;text-align:center;\n  opacity:0;transition:opacity .4s ease;\n}\n.eee-uni.on{opacity:1}\n#eee-title .eee-wave{fill:none;stroke:var(--ii-wave);stroke-width:3.4;stroke-linejoin:miter;filter:drop-shadow(1.5px 2px 1.5px rgba(10,30,52,.45))}\n#eee-title text{font-family:var(--ii-title);font-weight:700;font-size:30px;fill:var(--ii-navy);opacity:0}\n#eee-title text.on{opacity:1}\n\n\n@media (prefers-reduced-motion:reduce){\n  #eee-intro::before,.eee-scroll{animation:none}\n}\n";
  document.head.appendChild(style);
  document.body.insertAdjacentHTML('beforeend', "<div id=\"eee-intro\" role=\"img\" aria-label=\"Department of Electrical and Electronic Engineering\">\n  <svg id=\"eee-logo\" viewBox=\"510 55 785 752\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" aria-hidden=\"true\">\n    <defs>\n      <linearGradient id=\"eee-paint0\" x1=\"720.59\" y1=\"586.987\" x2=\"728.258\" y2=\"722.916\" gradientUnits=\"userSpaceOnUse\">\n        <stop stop-color=\"#0A1E34\"/><stop offset=\"1\" stop-color=\"#1E599A\"/>\n      </linearGradient>\n      <linearGradient id=\"eee-paint1\" x1=\"710.846\" y1=\"586.987\" x2=\"718.513\" y2=\"722.916\" gradientUnits=\"userSpaceOnUse\">\n        <stop stop-color=\"#0A1E34\" stop-opacity=\"0.25\"/><stop offset=\"1\" stop-color=\"#1E599A\"/>\n      </linearGradient>\n      <clipPath id=\"eee-quarter\"><rect x=\"856.563\" y=\"59.0952\" width=\"434.437\" height=\"410.649\"/></clipPath>\n      <clipPath id=\"eee-clipB\"><rect x=\"531.107\" y=\"235\" width=\"73.927\" height=\"80\"/></clipPath>\n      <clipPath id=\"eee-clipY\"><rect x=\"527.483\" y=\"265\" width=\"75.498\" height=\"80\"/></clipPath>\n      <clipPath id=\"eee-clipR\"><rect x=\"527\" y=\"323\" width=\"73.927\" height=\"80\"/></clipPath>\n    </defs>\n\n    <!-- tower and its shadow -->\n    <path fill=\"url(#eee-paint0)\" d=\"M697.562 512.5C689.804 549.493 685.175 569.213 655.638 603.476C655.638 603.476 603.025 604.045 597.512 604.045C592 604.045 597.512 657.493 597.512 657.493C597.512 657.493 540.5 666.5 534 657.493C527.5 648.487 524 733.5 534 728C544 722.5 895 722 906 728C917 734 916.5 649.987 906 657.493C895.5 665 837.649 657.493 837.649 657.493C837.649 657.493 844.797 601.59 837.649 604.045C830.5 606.5 770.781 603.476 770.781 603.476C746.754 570.694 735.458 550.622 731.219 510.226L727.676 386.27H744.21C749.223 388.649 751.74 390.768 753.657 395.937C753.657 395.937 755.814 374.434 753.657 375.467C751.5 376.5 727.676 375.467 727.676 375.467V358.409C730.16 353.742 731.692 351.917 737.124 350.449H769.01C778.233 354.675 779.024 357.821 782 362.389V341.92L727.086 341.351L727.676 311.784H745.391C750.914 312.034 751.988 317.472 754.248 322.018C754.248 322.018 757 303 754.248 301.549C751.495 300.098 720 302.5 721.181 301.549C722.362 300.598 721.181 297 721.181 297H702.876C702.876 297 702 300.5 702.876 301.549C703.752 302.598 674.524 299.598 672.762 301.549C671 303.5 672.762 322.018 672.762 322.018C675.406 315.036 676.841 311.466 681.029 311.784H697.562V341.351C697.562 341.351 650.5 341.92 646.781 341.351C643.062 340.782 646.781 362.389 646.781 362.389C651.053 355.542 653.84 352.77 659.771 350.449H691.067C695.486 352.73 697.371 354.269 697.562 358.409V375.467C697.562 375.467 674.524 374.33 672.762 374.898C671 375.467 672.762 396.505 672.762 396.505C674.824 388.642 677.485 385.204 684.571 386.27H698.152L697.562 512.5Z\"/>\n    <path fill=\"url(#eee-paint1)\" d=\"M687.818 512.5C680.06 549.493 675.431 569.213 645.894 603.476C645.894 603.476 593.28 604.045 587.768 604.045C582.256 604.045 587.768 657.493 587.768 657.493C587.768 657.493 530.756 666.5 524.256 657.493C517.756 648.487 514.256 733.5 524.256 728C534.256 722.5 885.256 722 896.255 728C907.255 734 906.755 649.987 896.255 657.493C885.756 665 827.904 657.493 827.904 657.493C827.904 657.493 835.053 601.59 827.904 604.045C820.756 606.5 761.037 603.476 761.037 603.476C737.01 570.694 725.714 550.622 721.475 510.226L717.932 386.27H734.465C739.479 388.649 741.995 390.768 743.913 395.937C743.913 395.937 746.07 374.434 743.913 375.467C741.756 376.5 717.932 375.467 717.932 375.467V358.409C720.416 353.742 721.948 351.917 727.379 350.449H759.265C768.488 354.675 769.28 357.821 772.256 362.389V341.92L717.341 341.351L717.932 311.784H735.646C741.169 312.034 742.243 317.472 744.503 322.018C744.503 322.018 747.256 303 744.503 301.549C741.751 300.098 710.256 302.5 711.437 301.549C712.618 300.598 711.437 297 711.437 297H693.132C693.132 297 692.256 300.5 693.132 301.549C694.008 302.598 664.779 299.598 663.018 301.549C661.256 303.5 663.018 322.018 663.018 322.018C665.662 315.036 667.097 311.466 671.284 311.784H687.818V341.351C687.818 341.351 640.756 341.92 637.037 341.351C633.318 340.782 637.037 362.389 637.037 362.389C641.309 355.542 644.095 352.77 650.027 350.449H681.322C685.741 352.73 687.627 354.269 687.818 358.409V375.467C687.818 375.467 664.779 374.33 663.018 374.898C661.256 375.467 663.018 396.505 663.018 396.505C665.08 388.642 667.741 385.204 674.827 386.27H688.408L687.818 512.5Z\"/>\n\n    <!-- arcs, smallest first -->\n    <g class=\"eee-arcs\" clip-path=\"url(#eee-quarter)\">\n      <path id=\"eee-arc1\"  stroke-width=\"9.31372\" d=\"M854.219 437.899C869.46 437.899 881.598 449.891 881.598 464.42C881.598 478.95 869.46 490.943 854.219 490.943C838.978 490.943 826.84 478.95 826.84 464.42C826.84 449.891 838.978 437.899 854.219 437.899Z\"/>\n      <path id=\"eee-arc2\"  stroke-width=\"9.31372\" d=\"M855 407.481C886.208 407.481 911.289 432.071 911.289 462.14C911.289 492.209 886.207 516.798 855 516.798C823.793 516.798 798.711 492.209 798.711 462.14C798.711 432.071 823.792 407.481 855 407.481Z\"/>\n      <path id=\"eee-arc3\"  stroke-width=\"9.31372\" d=\"M851.874 375.541C902.932 375.541 944.107 415.792 944.107 465.181C944.107 514.57 902.933 554.822 851.874 554.822C800.816 554.821 759.643 514.57 759.643 465.181C759.643 415.792 800.816 375.541 851.874 375.541Z\"/>\n      <path id=\"eee-arc4\"  stroke-width=\"9.31372\" d=\"M840.154 332.955C919.262 332.956 983.175 395.337 983.175 472.025C983.175 548.713 919.262 611.095 840.154 611.095C761.047 611.095 697.134 548.713 697.134 472.025C697.134 395.337 761.047 332.955 840.154 332.955Z\"/>\n      <path id=\"eee-arc5\"  stroke-width=\"9.31372\" d=\"M840.936 293.411C946.367 293.412 1031.62 376.562 1031.62 478.87C1031.62 581.177 946.367 664.327 840.936 664.328C735.504 664.328 650.252 581.177 650.252 478.87C650.252 376.562 735.504 293.411 840.936 293.411Z\"/>\n      <path id=\"eee-arc6\"  stroke-width=\"9.31372\" d=\"M847.967 250.826C971.092 250.826 1070.69 347.935 1070.69 467.462C1070.69 586.99 971.092 684.1 847.967 684.1C724.843 684.1 625.249 586.989 625.249 467.462C625.249 347.935 724.843 250.826 847.967 250.826Z\"/>\n      <path id=\"eee-arc7\"  stroke-width=\"9.31372\" d=\"M851.874 199.114C1001.32 199.114 1122.26 316.992 1122.26 462.139C1122.26 607.285 1001.32 725.164 851.874 725.164C702.426 725.164 581.492 607.285 581.492 462.139C581.493 316.993 702.426 199.115 851.874 199.114Z\"/>\n      <path id=\"eee-arc8\"  stroke-width=\"9.31372\" d=\"M840.935 158.05C1023.18 158.05 1170.7 301.804 1170.7 478.87C1170.7 655.936 1023.18 799.69 840.935 799.69C658.691 799.69 511.17 655.936 511.17 478.87C511.17 301.804 658.691 158.05 840.935 158.05Z\"/>\n      <path id=\"eee-arc9\"  stroke-width=\"9.76013\" d=\"M854.218 105.04C1059.22 105.04 1225.17 266.745 1225.17 465.941C1225.17 665.138 1059.22 826.843 854.218 826.843C649.22 826.843 483.263 665.138 483.263 465.941C483.264 266.745 649.22 105.04 854.218 105.04Z\"/>\n      <path id=\"eee-arc10\" stroke-width=\"10.4297\" d=\"M878.441 70.3937C1097.5 70.3937 1274.85 243.193 1274.85 456.056C1274.85 668.918 1097.5 841.717 878.441 841.717C659.378 841.717 482.036 668.918 482.036 456.056C482.036 243.193 659.378 70.3937 878.441 70.3937Z\"/>\n    </g>\n\n    <!-- antenna: poles, dish filled, then the dish shadow -->\n    <path stroke=\"black\" stroke-width=\"1.38108\" d=\"M789.513 612.5V518.586M814.373 612.5V530.326M804.705 508.228L828.184 486.821M786.751 490.965L828.184 486.821L833.018 525.492\"/>\n    <path fill=\"#000\" stroke=\"black\" stroke-width=\"1.38108\" d=\"M770.869 435C768.982 456.843 770.394 469.781 772.94 491.624C776.515 503.144 777.973 508.524 787.442 518.556C797.142 524.584 802.656 528.953 812.992 531.676C825.25 535.786 832.16 535.386 840.613 536.51L871.688 537.2L855.805 533.748C846.167 531.564 841.041 528.668 832.327 525.461C823.872 521.957 819.178 519.45 810.92 513.722L801.253 506.126L794.347 499.911C792.562 499.498 783.298 486.791 779.155 475.051C776.393 463.312 776.506 467.746 773.631 450.192L770.869 435Z\"/>\n    <path fill=\"#032D5B\" fill-opacity=\"0.2\" d=\"M769.065 494.336C766.41 471.446 764.939 457.889 766.906 435L769.785 450.919C772.781 469.314 772.664 464.668 775.543 476.969C779.862 489.271 789.518 502.586 791.38 503.019L798.578 509.532L808.655 517.492C817.264 523.494 822.157 526.121 830.97 529.793C840.053 533.154 845.397 536.188 855.444 538.476L872 542.094L839.608 541.371C830.796 540.193 823.593 540.612 810.815 536.305C800.041 533.453 794.293 528.874 784.181 522.557C774.311 512.044 772.791 506.407 769.065 494.336Z\"/>\n    <path stroke=\"black\" stroke-opacity=\"0.2\" stroke-width=\"1.38108\" d=\"M786.341 621V522.589M812.255 621V534.89M802.177 511.735L826.651 489.303M783.462 493.645L826.651 489.303L831.69 529.825M766.906 435C764.939 457.889 766.41 471.446 769.065 494.336C772.791 506.407 774.311 512.044 784.181 522.557C794.293 528.874 800.041 533.453 810.815 536.305C823.593 540.612 830.796 540.193 839.608 541.371L872 542.094L855.444 538.476C845.397 536.188 840.053 533.154 830.97 529.793C822.157 526.121 817.264 523.494 808.655 517.492L798.578 509.532L791.38 503.019C789.518 502.586 779.862 489.271 775.543 476.969C772.664 464.668 772.781 469.314 769.785 450.919L766.906 435Z\"/>\n\n    <!-- your three sine waves, each repeated once so it can scroll without a jump -->\n    <g clip-path=\"url(#eee-clipB)\"><g class=\"eee-scroll\" style=\"--p:-73.927px\">\n      <path id=\"eee-wB\" stroke=\"#1C0097\" stroke-width=\"2.77186\" d=\"M531.107 281.702C547.641 259.307 556.157 259.558 570.124 281.702C583.509 305 591.136 306.381 605.034 281.702\"/>\n      <use href=\"#eee-wB\" x=\"73.927\"/>\n    </g></g>\n    <g clip-path=\"url(#eee-clipY)\"><g class=\"eee-scroll\" style=\"--p:-75.498px\">\n      <path id=\"eee-wY\" stroke=\"#FFFF00\" stroke-width=\"2.77186\" d=\"M527.483 311.5C544.017 289.105 552.533 289.356 566.5 311.5C579.885 334.798 589.082 334.171 602.981 309.492\"/>\n      <use href=\"#eee-wY\" x=\"75.498\"/>\n    </g></g>\n    <g clip-path=\"url(#eee-clipR)\"><g class=\"eee-scroll\" style=\"--p:-73.927px\">\n      <path id=\"eee-wR\" stroke=\"#FF0004\" stroke-width=\"2.77186\" d=\"M527 369.702C543.534 347.307 552.05 347.558 566.017 369.702C579.402 393 587.029 394.381 600.927 369.702\"/>\n      <use href=\"#eee-wR\" x=\"73.927\"/>\n    </g></g>\n\n    <ellipse cx=\"719.5\" cy=\"793.5\" rx=\"144.5\" ry=\"8.5\" fill=\"#0A1E34\" fill-opacity=\"0.15\"/>\n  </svg>\n\n  <svg id=\"eee-title\" xmlns=\"http://www.w3.org/2000/svg\" aria-hidden=\"true\"></svg>\n  <div class=\"eee-uni\" id=\"eee-uni\">University of Chittagong</div>\n</div>");
})();
(() => {
  const NS = 'http://www.w3.org/2000/svg';
  const intro = document.getElementById('eee-intro');
    const titleSvg = document.getElementById('eee-title');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const arcs = Array.from({length:10}, (_, i) => document.getElementById('eee-arc' + (i + 1)));

  const TITLE = 'ELECTRICAL AND ELECTRONIC ENGINEERING';
  const GAP = 3, LEAD = 18, ROW_GAP = 64, BASE = 40, LOW = BASE + 6;
  let rowsInfo;

  /* Nabiha's own square wave from Figma, stretched to fit each row.
     It has three levels (888 high, 926 middle, 964 low) and uneven pulse widths. */
  const HER = 'M-2 926H49.1538V888H94.4615V926H132.462V964H169V926H212.846V888H256.692V926H328.308V888H380.923V926H430.615V964H468.615V926H530V964H569.462V926H613.308V888H664.462V926H703.923V964H740.462V926H779V888H823.5V964H867V926H907V888H964V926H1003.5V964H1050V926V888H1093V926H1131V964H1173.5V926H1216.5V888H1261.5V926H1301.5V964H1339V926H1377V888H1413.5V926H1440';
  const herPts = (() => {
    const pts = []; let x = 0, y = 0;
    HER.match(/[MHV]-?[\d.]+(?:\s-?[\d.]+)?/g).forEach(tok => {
      const c = tok[0], nums = tok.slice(1).trim().split(/\s+/).map(Number);
      if (c === 'M') { x = nums[0]; y = nums[1]; }
      else if (c === 'H') x = nums[0];
      else y = nums[0];
      pts.push([x, y]);
    });
    return pts;
  })();
  const WAVE_TALL = 42;                         // a little taller than the capital letters
  const MID = BASE - 11;                        // middle of the letters
  function herWave(x0, x1, dy) {
    const sx = (x1 - x0) / 1442, sy = WAVE_TALL / 76;
    return herPts.map(([x, y], i) =>
      (i ? 'L' : 'M') + (x0 + (x + 2) * sx).toFixed(2) + ' ' + (MID + dy + (y - 926) * sy).toFixed(2)
    ).join('');
  }

  function measure(ch) {
    const t = document.createElementNS(NS, 'text');
    t.textContent = ch === ' ' ? ' ' : ch;
    titleSvg.appendChild(t);
    const w = t.getComputedTextLength();
    t.remove();
    return w;
  }

  /* ---- title: the square wave slides across the row and the words appear behind it ---- */
  function buildTitle() {
    titleSvg.innerHTML = '';
    const rows = intro.clientWidth < 640 ? ['ELECTRICAL AND', 'ELECTRONIC', 'ENGINEERING'] : [TITLE];
    const widths = rows.map(r => [...r].reduce((s, ch) => s + measure(ch) + GAP, 0));
    const maxW = Math.max(...widths);
    titleSvg.setAttribute('viewBox', `${-LEAD - 4} 0 ${maxW + 2 * LEAD + 8} ${LOW + (rows.length - 1) * ROW_GAP + 10}`);
    rowsInfo = [];

    rows.forEach((row, r) => {
      const dy = r * ROW_GAP;
      const rowStart = (maxW - widths[r]) / 2;
      const rowEnd = rowStart + widths[r];

      // letters, hidden behind a clip that grows as the wave passes
      const tClip = document.createElementNS(NS, 'clipPath');
      tClip.id = 'eee-textclip' + r;
      const tRect = document.createElementNS(NS, 'rect');
      tRect.setAttribute('x', rowStart - 4);
      tRect.setAttribute('y', dy);
      tRect.setAttribute('width', 0);
      tRect.setAttribute('height', LOW + 8);
      tClip.appendChild(tRect);
      titleSvg.appendChild(tClip);
      const tg = document.createElementNS(NS, 'g');
      tg.setAttribute('clip-path', `url(#eee-textclip${r})`);
      let x = rowStart;
      [...row].forEach(ch => {
        const w = measure(ch) + GAP;
        if (ch !== ' ') {
          const t = document.createElementNS(NS, 'text');
          t.setAttribute('x', x + GAP / 2);
          t.setAttribute('y', BASE + dy);
          t.textContent = ch;
          t.classList.add('on');
          tg.appendChild(t);
        }
        x += w;
      });
      titleSvg.appendChild(tg);

      // the wave: a stretch of your square wave, kept inside the row
      const wClip = document.createElementNS(NS, 'clipPath');
      wClip.id = 'eee-waveclip' + r;
      const wRect = document.createElementNS(NS, 'rect');
      wRect.setAttribute('x', rowStart - LEAD);
      wRect.setAttribute('y', dy - 4);
      wRect.setAttribute('width', widths[r] + 2 * LEAD);
      wRect.setAttribute('height', LOW + 16);
      wClip.appendChild(wRect);
      titleSvg.appendChild(wClip);
      const wg = document.createElementNS(NS, 'g');
      wg.setAttribute('clip-path', `url(#eee-waveclip${r})`);
      const p = document.createElementNS(NS, 'path');
      p.setAttribute('class', 'eee-wave');
      p.setAttribute('d', herWave(rowStart - LEAD, rowEnd + LEAD, dy));
      wg.appendChild(p);
      titleSvg.appendChild(wg);

      rowsInfo.push({ tRect, wRect, rowStart, rowEnd });
    });
  }

  // u goes 0 → 1 for one row: an edge moves left to right; the wave vanishes behind it and the letters appear
  function setRow(r, u) {
    const e = u < .5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;   // gentle ease in and out
    const from = r.rowStart - LEAD, to = r.rowEnd + LEAD + 4;
    const edge = from + e * (to - from);
    r.wRect.setAttribute('x', edge);
    r.wRect.setAttribute('width', Math.max(0, to - edge));
    r.tRect.setAttribute('width', Math.max(0, edge - r.rowStart + 4));
  }

  /* ---- timeline: about 2.5 seconds, then the account page opens ---- */
  const T_SLIDE = 100, HOLD = 500;   // HOLD = pause after the title is written, before the fade (ms)
  const uni = document.getElementById('eee-uni');
  let t0, raf, done, slideMs, goNext, lettersDone;

  function setArcs(t) {
    // arcs switch on one by one from the smallest outwards, then switch off from the largest inwards
    const n = arcs.length, step = 110;
    const period = 2 * (n + 1) * step;
    const k = Math.floor((t % period) / step);
    const lit = k <= n ? k : 2 * n + 1 - k;
    arcs.forEach((a, i) => a.style.opacity = i < lit ? 1 : 0);
  }

  function frame(now) {
    const t = now - t0;
    setArcs(t);
    if (!lettersDone) {
      const s = t - T_SLIDE;
      rowsInfo.forEach((r, i) => setRow(r, Math.min(Math.max((s - i * slideMs) / slideMs, 0), 1)));
      if (s >= rowsInfo.length * slideMs) {
        lettersDone = true;
        uni.classList.add('on'); setTimeout(finish, HOLD);
      }
    }
    raf = requestAnimationFrame(frame);
  }

  function finish() {
    if (done) return;
    done = true;
    if (goNext) goNext();          // the screen stays up until the next page replaces it
  }

  // call eeeLoader(fn): plays the logo, then runs fn (usually: go to the account page)
  window.eeeLoader = async function (fn) {
    cancelAnimationFrame(raf);        // a page can play it twice (arriving, then leaving): stop the old loop first
    goNext = fn; done = false; lettersDone = false;
    uni.classList.remove('on');
    intro.classList.add('play');
    document.documentElement.style.overflow = 'hidden';
    // wait for the title font, but never more than a moment
    try { await Promise.race([document.fonts.load('700 30px Montserrat'), new Promise(r => setTimeout(r, 300))]); } catch (e) {}
    buildTitle();
    slideMs = rowsInfo.length > 1 ? 400 : 1000;   // how long the title takes to appear (ms): phone (per line) : computer
    if (reduce) {
      arcs.forEach(a => a.style.opacity = 1);
      rowsInfo.forEach(r => setRow(r, 1));
      uni.classList.add('on');
      setTimeout(finish, 900);
      return;
    }
    await new Promise(r => setTimeout(r, 450));        // let the 0.5 s fade-in finish first
    t0 = performance.now();
    raf = requestAnimationFrame(frame);
  };

  intro.addEventListener('click', finish);
  addEventListener('keydown', () => { if (intro.classList.contains('play')) finish(); });
})();

/* An account page opened in a new tab plays the screen on arrival, then shows the page. */
(() => {
  if (location.hash !== '#intro' || !window.eeeLoader) return;
  history.replaceState(null, '', location.pathname + location.search);   // tidy the address
  const intro = document.getElementById('eee-intro');
  eeeLoader(() => {
    intro.style.transition = 'opacity .4s ease';
    intro.style.opacity = '0';
    setTimeout(() => {
      intro.classList.remove('play');
      intro.style.opacity = intro.style.transition = '';
      document.documentElement.style.overflow = '';
    }, 400);
  });
})();

/* Leave for another page with the loading screen first (falls back to going straight there). */
window.eeeGo = function (url) {
  if (window.eeeLoader) eeeLoader(() => { location.href = url; });
  else location.href = url;
};
