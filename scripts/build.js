/* VERTI offline static site generator. Built-in Node.js modules only. */
function build() {
  const fs = require("node:fs");
  const path = require("node:path");
  const root = process.cwd();
  const out = path.join(root, "dist");
  const read = (p) => JSON.parse(fs.readFileSync(path.join(root, p), "utf8"));
  const site = read("content/site.json");
  const entries = read("content/articles.json").articles;
  const categories = site.categories;
  const langs = ["vi","en"];
  const categoryIds = categories.map(c => c.id);
  if (new Set(categoryIds).size !== categoryIds.length || categoryIds.some(id => typeof id !== "string" || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id))) {
    throw new Error("Invalid or duplicate editorial coverage category ID");
  }
  const escape = (value) => String(value ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
  const safeUrl = (v) => {
    const str = String(v ?? "");
    if (str.startsWith("/") && !str.startsWith("//")) return str;
    if (/^https:\/\/[^\s<>"']+$/i.test(str)) return str;
    throw new Error("Unsafe or invalid link: " + str);
  };
  const other = (lang) => lang === "vi" ? "en" : "vi";
  const prefix = (lang) => lang === "vi" ? "/" : "/en/";
  const articlePath = (a,lang) => prefix(lang) + "articles/" + a.slug + "/";
  const topicPath = (category, lang) => prefix(lang) + "topics/" + category.id + "/";
  const sections = (item,lang) => item[lang] || [];
  const dateOnly = (s,lang) => new Date(s).toLocaleDateString(lang === "vi" ? "vi-VN" : "en-GB", {timeZone:"UTC",day:"2-digit",month:"long",year:"numeric"});
  const ensure = (where, dir = out) => fs.mkdirSync(path.join(dir,where),{recursive:true});
  const write = (relative, body) => {
    const dest = path.join(out,relative);
    fs.mkdirSync(path.dirname(dest),{recursive:true});
    fs.writeFileSync(dest,body);
  };
  const published = [];
  const used = new Set();
  const localImages = new Set();
  function localImagePath(src) {
    if (!src.startsWith("/")) return null;
    const url = new URL(src, "https://verti.ch");
    const relative = decodeURIComponent(url.pathname).slice(1);
    if (url.origin !== "https://verti.ch" ||
        !/^images\/(?:[A-Za-z0-9_-]+\/)*[A-Za-z0-9_-]+\.[A-Za-z0-9]+$/.test(relative) ||
        !src.startsWith("/images/")) {
      throw new Error("Invalid local article image path: " + src);
    }
    return relative;
  }
  for (const a of entries) {
    if (a.status !== "published") continue;
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(a.slug || "")) throw new Error("Invalid article slug: " + a.slug);
    if (used.has(a.slug)) throw new Error("Duplicate slug: " + a.slug);
    used.add(a.slug);
    if (!categories.some(c=>c.id===a.category)) throw new Error("Invalid category: " + a.category);
    if (!a.date || isNaN(Date.parse(a.date))) throw new Error("Invalid article date: " + a.slug);
    if (!a.title?.vi || !a.title?.en || !a.summary?.vi || !a.summary?.en) throw new Error("Missing bilingual title/summary: "+a.slug);
    if (!a.body?.vi?.length || !a.body?.en?.length) throw new Error("Missing verified bilingual body: " + a.slug);
    if (!a.source?.url || !a.source?.name) throw new Error("Missing source: "+a.slug);
    safeUrl(a.source.url);
    if (a.facebookPost) safeUrl(a.facebookPost);
    if (a.facebookReel) safeUrl(a.facebookReel);
    for (const img of a.images || []) {
      const src = safeUrl(img.src);
      if (!img.alt?.vi || !img.alt?.en || !img.credit) throw new Error("Image alt/credit missing: " + a.slug);
      const relative = localImagePath(src);
      if (relative) {
        const file = path.join(root, "src", relative);
        if (!fs.existsSync(file) || !fs.statSync(file).isFile()) {
          throw new Error("Missing local article image for " + a.slug + ": " + relative);
        }
        localImages.add(relative);
      }
    }
    published.push(a);
  }
  published.sort((a,b) => new Date(b.date) - new Date(a.date));
  const byCategory = new Map(categories.map(category => [category.id, []]));
  for (const article of published) byCategory.get(article.category).push(article);
  const strings = {
    vi: {
      navLatest:"Tin mới", navTopics:"Chuyên mục", navAbout:"Giới thiệu", navArchive:"Tất cả bài",
      kicker:"Bản tin độc lập · Việt Nam và thế giới",
      lead:"Thông tin được kiểm chứng và biên tập dễ hiểu về WIPO, WTO, sở hữu trí tuệ và công nghệ tiên phong.",
      action:"Khám phá bài viết", follow:"Theo dõi Facebook", section:"Tin mới nhất", coverage:"Lĩnh vực theo dõi",
      emptyTitle:"Bài viết đang được chuẩn bị", emptyBody:"Website đã sẵn sàng tiếp nhận các bài báo đã kiểm chứng. Chưa có bài nào được công bố trên kho GitHub.",
      all:"Xem toàn bộ bài viết", archiveTitle:"Kho bài viết", archiveLead:"Các tin tức và phân tích đã xuất bản, phân loại theo thời gian.",
      topicCount:n=>n+" bài đã đăng", topicEmptyTitle:"Chưa có bài viết", topicEmptyBody:"Chuyên mục này chưa có bài nào được xuất bản.",
      topicReturn:"Tất cả chuyên mục", read:"Đọc bài", source:"Nguồn gốc", fb:"Bài Facebook", reel:"Xem Reel", home:"Trang chủ",
      published:"Ngày đăng", related:"Tin khác", imageCredit:"Nguồn ảnh",
      aboutTitle:"Một góc nhìn độc lập.", about:"VERTI tổng hợp và biên tập thông tin từ các nguồn công khai, đáng tin cậy. Đây không phải là kênh thông tin chính thức của WIPO, WTO hoặc cơ quan nhà nước.",
      principlesTitle:"Dữ kiện trước tiêu đề.", principles:"Thông tin được kiểm chứng trước khi xuất bản. Bài báo nêu rõ nguồn, thời điểm và liên kết tham khảo.",
      note:"Bản tin độc lập · Song ngữ Việt–Anh", notFound:"Không tìm thấy nội dung"
    },
    en: {
      navLatest:"Latest", navTopics:"Coverage", navAbout:"About", navArchive:"All stories",
      kicker:"Independent publication · Viet Nam & the world",
      lead:"Verified developments and clear analysis on WIPO, WTO, intellectual property and frontier technologies.",
      action:"Explore stories", follow:"Follow on Facebook", section:"Latest stories", coverage:"Editorial coverage",
      emptyTitle:"Stories are being prepared", emptyBody:"The platform is ready for verified news and analysis. No articles have yet been published from the GitHub repository.",
      all:"Browse all stories", archiveTitle:"Article archive", archiveLead:"Published news and analysis, sorted by date.",
      topicCount:n=>n+(n===1?" published story":" published stories"), topicEmptyTitle:"No stories yet", topicEmptyBody:"No stories have been published in this topic yet.",
      topicReturn:"All topics", read:"Read story", source:"Primary source", fb:"Facebook post", reel:"Watch Reel", home:"Home",
      published:"Published", related:"More stories", imageCredit:"Image credit",
      aboutTitle:"An independent perspective.", about:"VERTI curates and explains information from trustworthy public sources. It is not an official channel of WIPO, WTO or any government body.",
      principlesTitle:"Evidence before headlines.", principles:"Information is checked before publication. Each article identifies its source, date and supporting references.",
      note:"Independent publication · Vietnamese–English", notFound:"Content not found"
    }
  };
  function h(title,description,lang,uri,kind="website",image="") {
    const url = site.origin + uri;
    const vi = uri.replace(/^\/en\//,"/").replace(/^\/en$/,"/") || "/";
    const en = vi === "/" ? "/en/" : "/en" + vi;
    const safeTitle = escape(title);
    const safeDescription = escape(description);
    const json = JSON.stringify({"@context":"https://schema.org","@type":kind === "article" ? "NewsArticle" : "WebSite",headline:title,name:kind === "article" ? title:"VERTI",url,description}).replace(/</g,"\\u003c");
    return '<!doctype html><html lang="'+lang+'"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0b182d">'+
    '<title>'+safeTitle+' | VERTI</title><meta name="description" content="'+safeDescription+'">'+
    '<link rel="canonical" href="'+escape(url)+'"><link rel="alternate" hreflang="vi" href="'+escape(site.origin+vi)+'"><link rel="alternate" hreflang="en" href="'+escape(site.origin+en)+'">'+
    '<meta property="og:type" content="'+(kind==="article"?"article":"website")+'"><meta property="og:title" content="'+safeTitle+'"><meta property="og:description" content="'+safeDescription+'"><meta property="og:url" content="'+escape(url)+'">'+
    '<meta property="og:locale" content="'+(lang==="vi"?"vi_VN":"en_US")+'">'+(image?'<meta property="og:image" content="'+escape(image)+'">':'')+
    '<link rel="icon" type="image/svg+xml" href="/favicon.svg"><link rel="stylesheet" href="/style.css"><script type="application/ld+json">'+json+'</script></head><body>';
  }
  function nav(lang,langLink) {
    const s = strings[lang];
    return '<a class="skip" href="#main">Skip to content</a><header class="site-header"><div class="shell header-row"><a class="logo" href="'+prefix(lang)+'" aria-label="VERTI homepage">VER<span>TI</span><small>INSIGHT & INNOVATION</small></a>'+
    '<nav aria-label="Main navigation"><a href="'+prefix(lang)+'#latest">'+s.navLatest+'</a><a href="'+prefix(lang)+'#coverage">'+s.navTopics+'</a><a href="'+prefix(lang)+'#mission">'+s.navAbout+'</a><a href="'+prefix(lang)+'archive/">'+s.navArchive+'</a></nav>'+
    '<div class="lang" role="group" aria-label="Language"><a href="'+(lang==="vi"?langLink:langLink.replace(/\/en\//,"/"))+'" class="'+(lang==="vi"?"active":"")+'" lang="vi" hreflang="vi">VI</a><a href="'+(lang==="en"?langLink:langLink.replace(/^(\/)(?!en\/)/,"/en/"))+'" class="'+(lang==="en"?"active":"")+'" lang="en" hreflang="en">EN</a></div></div></header>';
  }
  function langNav(lang,otherUri) {
    const vi = lang === "vi" ? null : otherUri;
    const en = lang === "en" ? null : otherUri;
    return '<div class="lang" role="group" aria-label="Language"><a class="'+(lang==="vi"?"active":"")+'" href="'+(vi || (otherUri.startsWith("/en/") ? otherUri.replace(/^\/en\//,"/") : otherUri))+'" lang="vi">VI</a><a class="'+(lang==="en"?"active":"")+'" href="'+(en || (otherUri.startsWith("/en/") ? otherUri : "/en"+otherUri))+'" lang="en">EN</a></div>';
  }
  function header(lang,uriVi,uriEn) {
    const s = strings[lang];
    return '<a class="skip" href="#main">Skip to main content</a><header class="site-header"><div class="shell header-row"><a class="logo" href="'+prefix(lang)+'">VER<span>TI</span><small>INSIGHT & INNOVATION</small></a>'+
    '<nav aria-label="Navigation"><a href="'+prefix(lang)+'#latest">'+s.navLatest+'</a><a href="'+prefix(lang)+'#coverage">'+s.navTopics+'</a><a href="'+prefix(lang)+'#mission">'+s.navAbout+'</a><a href="'+prefix(lang)+'archive/">'+s.navArchive+'</a></nav>'+
    '<div class="lang" role="group" aria-label="Chọn ngôn ngữ / Choose language"><a class="'+(lang==="vi"?"active":"")+'" href="'+uriVi+'" lang="vi" hreflang="vi">VI</a><a class="'+(lang==="en"?"active":"")+'" href="'+uriEn+'" lang="en" hreflang="en">EN</a></div></div></header>';
  }
  function footer(lang) {
    return '<footer><div class="shell foot"><div>© '+new Date().getUTCFullYear()+' VERTI · verti.ch</div><p>'+strings[lang].note+'</p><div class="footlinks"><a href="https://www.wipo.int/" target="_blank" rel="noopener noreferrer">WIPO</a><a href="https://www.wto.org/" target="_blank" rel="noopener noreferrer">WTO</a><a href="'+safeUrl(site.facebook)+'" target="_blank" rel="noopener noreferrer">Facebook</a></div></div></footer></body></html>';
  }
  function card(a,lang,heading="h3") {
    const cat = categories.find(c=>c.id===a.category);
    const s = strings[lang];
    const img = a.images?.length ? '<img loading="lazy" src="'+escape(safeUrl(a.images[0].src))+'" alt="'+escape(a.images[0].alt[lang])+'">' : '<div class="card-art"><span>'+escape(cat.label)+' / VERTI</span></div>';
    return '<article class="story-card"><a href="'+articlePath(a,lang)+'">'+img+'<div class="story-details"><p class="meta">'+escape(cat.name[lang])+' · '+dateOnly(a.date,lang)+'</p><'+heading+'>'+escape(a.title[lang])+'</'+heading+'><p class="excerpt">'+escape(a.summary[lang])+'</p><span class="read">'+s.read+' →</span></div></a></article>';
  }
  const all = (lang,limit=0) => published.slice(0,limit || undefined).map(a=>card(a,lang)).join("");
  function home(lang) {
    const s=strings[lang]; const uri=prefix(lang); const switchVi="/",switchEn="/en/";
    const cards=published.length?'<div class="stories">'+all(lang,9)+'</div>':
      '<div class="empty"><div class="dot"></div><h3>'+s.emptyTitle+'</h3><p>'+s.emptyBody+'</p></div>';
    const categoryCards=categories.map((c,i)=>'<a class="topic" href="'+topicPath(c,lang)+'"><span class="topic-no">'+String(i+1).padStart(2,"0")+' / '+escape(c.label)+'</span><h3>'+escape(c.name[lang])+'</h3><p>'+escape(c.description[lang])+'</p><span class="topic-card-count">'+s.topicCount(byCategory.get(c.id).length)+' <span aria-hidden="true">→</span></span></a>').join("");
    return h(lang==="vi"?"Tin tức công nghệ, sở hữu trí tuệ và thương mại thế giới":"Technology, intellectual property and world trade",s.lead,lang,uri)+header(lang,switchVi,switchEn)+
      '<section class="hero"><div class="shell hero-inner"><p class="kicker">'+s.kicker+'</p><h1>'+ (lang==="vi"?'Tin tức công nghệ,<br><em>sở hữu trí tuệ</em><br>và thương mại thế giới':'Technology,<br><em>intellectual property</em><br>and world trade') +'</h1><p class="hero-desc">'+s.lead+'</p><div class="hero-actions"><a class="btn gold" href="#latest">'+s.action+'</a><a class="btn outline" target="_blank" rel="noopener noreferrer" href="'+safeUrl(site.facebook)+'">'+s.follow+'</a></div><div class="hero-tags"><span>01 / INNOVATION</span><span>02 / INTELLECTUAL PROPERTY</span><span>03 / WORLD TRADE</span></div></div></section>'+
      '<main id="main" class="shell main"><section id="latest" class="latest"><div class="section-head"><div><p class="eyebrow">NEWSROOM</p><h2>'+s.section+'</h2></div><a class="all-link" href="'+uri+'archive/">'+s.all+' →</a></div>'+cards+'</section>'+
      '<section id="coverage" class="coverage"><div class="section-head"><div><p class="eyebrow">EDITORIAL COVERAGE</p><h2>'+s.coverage+'</h2></div></div><div class="topics">'+categoryCards+'</div></section>'+
      '<section id="mission" class="mission"><div><p class="eyebrow">ABOUT VERTI</p><h2>'+s.aboutTitle+'</h2><p>'+s.about+'</p></div><div><p class="eyebrow">EDITORIAL PRINCIPLES</p><h2>'+s.principlesTitle+'</h2><p>'+s.principles+'</p></div></section></main>'+footer(lang);
  }
  function archive(lang) {
    const s=strings[lang], uri=prefix(lang)+"archive/";
    return h(s.archiveTitle,s.archiveLead,lang,uri)+header(lang,"/archive/","/en/archive/")+
    '<main id="main" class="shell article-shell"><p class="eyebrow">VERTI / ARCHIVE</p><h1 class="page-title">'+s.archiveTitle+'</h1><p class="page-lead">'+s.archiveLead+'</p>'+
    (published.length?'<div class="stories">'+all(lang)+'</div>':'<div class="empty"><h2>'+s.emptyTitle+'</h2><p>'+s.emptyBody+'</p></div>')+
    '</main>'+footer(lang);
  }
  function renderTopic(category,lang) {
    const s = strings[lang], uri = topicPath(category,lang), articles = byCategory.get(category.id);
    const name = category.name[lang], description = category.description[lang];
    const list = articles.length
      ? '<div class="stories">'+articles.map(a=>card(a,lang,"h2")).join("")+'</div>'
      : '<div class="empty"><h2>'+s.topicEmptyTitle+'</h2><p>'+s.topicEmptyBody+'</p></div>';
    return h(name,description,lang,uri)+header(lang,topicPath(category,"vi"),topicPath(category,"en"))+
      '<main id="main" class="shell article-shell topic-page"><nav class="breadcrumbs" aria-label="'+(lang==="vi"?"Đường dẫn":"Breadcrumbs")+'"><a href="'+prefix(lang)+'#coverage">'+s.topicReturn+'</a> / <span aria-current="page">'+escape(name)+'</span></nav>'+
      '<p class="eyebrow">'+escape(category.label)+'</p><h1 class="page-title">'+escape(name)+'</h1><p class="page-lead">'+escape(description)+'</p>'+
      '<p class="topic-list-count">'+s.topicCount(articles.length)+'</p>'+list+
      '<p class="topic-back"><a class="all-link" href="'+prefix(lang)+'archive/">'+s.all+' →</a></p></main>'+footer(lang);
  }
  function renderArticle(a,lang) {
    const s=strings[lang],cat=categories.find(c=>c.id===a.category), uri=articlePath(a,lang);
    const figures=(a.images||[]).map(img=>'<figure><img loading="lazy" src="'+escape(safeUrl(img.src))+'" alt="'+escape(img.alt[lang])+'"><figcaption>'+s.imageCredit+': '+escape(img.credit)+'</figcaption></figure>').join("");
    const paragraphs=(a.body[lang]||[]).map(sec=>'<section class="article-section">'+(sec.heading?'<h2>'+escape(sec.heading)+'</h2>':'')+(sec.paragraphs||[]).map(p=>'<p>'+escape(p)+'</p>').join("")+'</section>').join("");
    const links='<aside class="source"><h2>'+s.source+'</h2><a rel="noopener noreferrer" target="_blank" href="'+safeUrl(a.source.url)+'">'+escape(a.source.name)+' ↗</a>'+
      (a.facebookPost?'<a rel="noopener noreferrer" target="_blank" href="'+safeUrl(a.facebookPost)+'">'+s.fb+' ↗</a>':'')+
      (a.facebookReel?'<a rel="noopener noreferrer" target="_blank" href="'+safeUrl(a.facebookReel)+'">'+s.reel+' ↗</a>':'')+'</aside>';
    const json = JSON.stringify({"@context":"https://schema.org","@type":"NewsArticle",headline:a.title[lang],datePublished:a.date,description:a.summary[lang],mainEntityOfPage:site.origin+uri,isAccessibleForFree:true,author:{"@type":"Organization",name:"VERTI"},publisher:{"@type":"Organization",name:"VERTI"},citation:a.source.url}).replace(/</g,"\\u003c");
    const image = a.images?.[0]?.src;
    return h(a.title[lang], a.summary[lang], lang, uri, "article", image ? new URL(image, site.origin).href : "")+
      header(lang,articlePath(a,"vi"),articlePath(a,"en"))+
      '<main id="main" class="shell article-shell"><nav class="breadcrumbs" aria-label="Breadcrumbs"><a href="'+prefix(lang)+'">'+s.home+'</a> / '+escape(cat.name[lang])+'</nav>'+
      '<p class="eyebrow">'+escape(cat.label)+' / '+s.published+' '+dateOnly(a.date,lang)+'</p><h1 class="page-title">'+escape(a.title[lang])+'</h1><p class="page-lead">'+escape(a.summary[lang])+'</p>'+
      '<div class="article-layout"><article class="article-body">'+figures+paragraphs+'</article>'+links+'</div>'+
      '<div class="read-more"><h2>'+s.related+'</h2><div class="stories">'+published.filter(x=>x.slug!==a.slug).slice(0,3).map(x=>card(x,lang)).join("")+'</div></div></main>'+
      '<script type="application/ld+json">'+json+'</script>'+footer(lang);
  }
  fs.rmSync(out,{recursive:true,force:true}); fs.mkdirSync(out,{recursive:true});
  fs.copyFileSync(path.join(root,"src/style.css"),path.join(out,"style.css"));
  fs.copyFileSync(path.join(root,"src/favicon.svg"),path.join(out,"favicon.svg"));
  for (const relative of localImages) {
    fs.mkdirSync(path.dirname(path.join(out, relative)), {recursive:true});
    fs.copyFileSync(path.join(root, "src", relative), path.join(out, relative));
  }
  for (const lang of langs) {
    const pre=lang==="vi"?"":"en/";
    write(pre+"index.html",home(lang));
    write(pre+"archive/index.html",archive(lang));
    for (const category of categories) write(topicPath(category,lang).slice(1)+"index.html",renderTopic(category,lang));
    for (const a of published) write(pre+"articles/"+a.slug+"/index.html",renderArticle(a,lang));
  }
  const urls=["/","/en/","/archive/","/en/archive/",...categories.flatMap(c=>[topicPath(c,"vi"),topicPath(c,"en")]),...published.flatMap(a=>[articlePath(a,"vi"),articlePath(a,"en")])];
  write("sitemap.xml",'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+urls.map(x=>"<url><loc>"+escape(site.origin+x)+"</loc></url>").join("")+"</urlset>");
  write("robots.txt","User-agent: *\nAllow: /\nSitemap: "+site.origin+"/sitemap.xml\n");
  const rssItems=published.slice(0,30).map(a=>'<item><title>'+escape(a.title.vi)+'</title><link>'+escape(site.origin+articlePath(a,"vi"))+'</link><guid>'+escape(site.origin+articlePath(a,"vi"))+'</guid><pubDate>'+new Date(a.date).toUTCString()+'</pubDate><description>'+escape(a.summary.vi)+'</description></item>').join("");
  write("rss.xml",'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>VERTI</title><link>'+site.origin+'</link><description>Vietnamese and English science, IP and world trade news</description><language>vi</language>'+rssItems+'</channel></rss>');
  write("_headers","/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n");
  console.log("VERTI: built "+published.length+" verified published stories in VI and EN; total output pages "+urls.length);
}
build();
