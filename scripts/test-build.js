/* Exercise the site generator through its production entry point. */
const assert = require("node:assert/strict");
const { execFileSync, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const fixture = fs.mkdtempSync(path.join(os.tmpdir(), "verti-build-"));
const build = path.join(root, "scripts", "build.js");
const read = relative => fs.readFileSync(path.join(fixture, relative), "utf8");
const exists = relative => fs.existsSync(path.join(fixture, relative));
try {
  fs.cpSync(path.join(root, "content"), path.join(fixture, "content"), {recursive: true});
  fs.cpSync(path.join(root, "src"), path.join(fixture, "src"), {recursive: true});
  const data = JSON.parse(read("content/articles.json"));
  const original = data.articles.find(article => article.status === "published");
  const image = {
    src: "/images/test/nested/sample.svg?v=1",
    alt: {vi: "Ảnh thử tiếng Việt", en: "English test image"},
    credit: "VERTI Test"
  };
  const bytes = '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"><circle r="1"/></svg>';
  fs.mkdirSync(path.join(fixture, "src/images/test/nested"), {recursive: true});
  fs.writeFileSync(path.join(fixture, "src/images/test/nested/sample.svg"), bytes);
  fs.writeFileSync(path.join(fixture, "src/images/draft-only.svg"), bytes);
  const story = {...original, slug: "regression-image", status: "published",
    images: [image, {...image, src: "https://example.com/allowed.jpg"}]};
  const draft = {...original, slug: "regression-private", status: "draft",
    images: [{...image, src: "/images/draft-only.svg"}]};
  const categories = JSON.parse(read("content/site.json")).categories;
  const emptyCategory = categories.find(c => c.id !== story.category);
  data.articles = data.articles.filter(a => a.category !== emptyCategory.id);
  draft.category = emptyCategory.id;
  const topicFixture = Array.from({length: 10}, (_,i) => ({
    ...original, slug: "regression-topic-"+i, status: "published",
    date: "2090-01-"+String(i+1).padStart(2,"0"), images: []
  }));
  const oldStory = {...original, slug:"regression-topic-old", status:"published", date:"2000-01-01", images:[]};
  data.articles.push(oldStory, story, draft, ...topicFixture);
  const expectedPublished = data.articles.filter(a=>a.status==="published")
    .sort((a,b)=>new Date(b.date)-new Date(a.date));
  const countLabel = (count,lang)=> lang==="vi"?count+" bài đã đăng":count+(count===1?" published story":" published stories");
  const save = () => fs.writeFileSync(path.join(fixture, "content/articles.json"), JSON.stringify(data));
  save();
  execFileSync(process.execPath, [build], {cwd: fixture});

  for (const [language, prefix, alt] of [
    ["vi", "", image.alt.vi], ["en", "en/", image.alt.en]
  ]) {
    const homepage = read("dist/" + prefix + "index.html");
    const article = read("dist/" + prefix + "articles/regression-image/index.html");
    const archive = read("dist/" + prefix + "archive/index.html");
    assert.ok(homepage.includes('lang="' + language + '"'));
    assert.ok(archive.includes("regression-image"));
    assert.ok(!archive.includes("regression-private"));
    assert.ok(article.includes('src="' + image.src + '"'));
    assert.ok(article.includes('alt="' + alt + '"'));
    assert.ok(article.includes("https://verti.ch" + image.src));
    assert.ok(!exists("dist/" + prefix + "articles/regression-private/index.html"));
    const langPath = "/" + prefix;
    const homeTopicPaths = [...homepage.matchAll(/<a class="topic" href="([^"]+)"/g)].map(x=>x[1]);
    const knownTopicPaths = categories.map(c=>langPath+"topics/"+c.id+"/");
    assert.deepEqual(homeTopicPaths, knownTopicPaths, "homepage exposes every configured topic as a native link");
    for (const category of categories) {
      const topicPath = langPath+"topics/"+category.id+"/";
      const topic = read("dist"+topicPath+"index.html");
      const expected = expectedPublished.filter(a=>a.category===category.id);
      const links = [...topic.matchAll(/<article class="story-card"><a href="([^"]+)"/g)].map(x=>x[1]);
      const homeCard = homepage.split('<a class="topic" href="'+topicPath+'">')[1].split("</a>")[0];
      assert.ok(homeCard.includes(countLabel(expected.length,language)));
      assert.ok(topic.includes('<p class="topic-list-count">'+countLabel(expected.length,language)+'</p>'));
      assert.deepEqual(links,expected.map(a=>langPath+"articles/"+a.slug+"/"),"topic list is exact, unpaginated, and newest first");
      assert.ok(topic.includes('<html lang="'+language+'">'));
      assert.ok(topic.includes('rel="canonical" href="https://verti.ch'+topicPath+'"'));
      assert.ok(topic.includes('href="/topics/'+category.id+'/" lang="vi"'));
      assert.ok(topic.includes('href="/en/topics/'+category.id+'/" lang="en"'));
      assert.ok(topic.includes('href="'+langPath+'archive/"'));
      if (!expected.length) assert.ok(topic.includes(language==="vi"?"Chưa có bài viết":"No stories yet"));
    }
    assert.ok(read("dist/sitemap.xml").includes("<loc>https://verti.ch"+langPath+"topics/"+emptyCategory.id+"/</loc>"));
    const archiveLinks = [...archive.matchAll(/<article class="story-card"><a href="([^"]+)"/g)].map(x=>x[1]);
    assert.deepEqual(archiveLinks,expectedPublished.map(a=>langPath+"articles/"+a.slug+"/"),"general archive sees all published stories, excluding drafts");
  }
  assert.equal(read("dist/images/test/nested/sample.svg"), bytes);
  assert.ok(!exists("dist/images/draft-only.svg"));
  assert.ok(!read("dist/sitemap.xml").includes("regression-private"));

  story.images[0].src = "/images/missing.svg";
  save();
  const failed = spawnSync(process.execPath, [build], {cwd: fixture, encoding: "utf8"});
  assert.notEqual(failed.status, 0);
  assert.match(failed.stderr, /Missing local article image for regression-image/);
  assert.equal(read("dist/images/test/nested/sample.svg"), bytes);
  console.log("Verified bilingual home/topic/archive routes, ordered exact topic counts and empty states, drafts excluded, and local image guards.");
} finally {
  fs.rmSync(fixture, {recursive: true, force: true});
}
