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
  data.articles.push(story, draft);
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
  console.log("Verified bilingual routes and local assets; drafts excluded; missing image blocks release.");
} finally {
  fs.rmSync(fixture, {recursive: true, force: true});
}
