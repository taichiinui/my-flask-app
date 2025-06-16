from flask import Flask, request, render_template
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)

# WordPress設定
WP_URL = "https://nrc-formula.com"
WP_USER = "ppcuser"
WP_APP_PASS = "bbop gpun Fckj oqLv jNP3 Bn5g"

def upload_image_to_wordpress(image_url):
    filename = image_url.split("/")[-1]
    img_data = requests.get(image_url).content

    if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
        content_type = "image/jpeg"
    elif filename.lower().endswith(".png"):
        content_type = "image/png"
    elif filename.lower().endswith(".gif"):
        content_type = "image/gif"
    elif filename.lower().endswith(".webp"):
        content_type = "image/webp"
    else:
        raise ValueError(f"未対応の画像形式: {filename}")

    headers = {
        'Content-Disposition': f'attachment; filename={filename}',
        'Content-Type': content_type
    }

    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/media",
        headers=headers,
        data=img_data,
        auth=(WP_USER, WP_APP_PASS)
    )
    response.raise_for_status()
    return response.json()["source_url"]

def process_html_and_replace_images(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for img in soup.find_all("img"):
        old_src = img.get("src")
        if not old_src:
            continue
        if old_src.startswith("data:"):  # base64の画像はスキップ
            print(f"[スキップ] インライン画像: {old_src[:30]}...")
            continue
        print(f"変換対象画像: {old_src}")
        try:
            new_src = upload_image_to_wordpress(old_src)
            print(f"→ WordPressにアップされた新画像URL: {new_src}")
            img["src"] = new_src
            # ✅ data-src属性も削除（元画像のURLが残らないように）
            if "data-src" in img.attrs:
                del img["data-src"]
        except Exception as e:
            print(f"[エラー] {old_src} の画像アップロードに失敗: {e}")
    return str(soup)


def strip_url_parameters_from_links_only(html):
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        a["href"] = a["href"].split("?")[0]
    return str(soup)

def rewrite_all_links(html, new_url):
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        a["href"] = new_url
    return str(soup)

def post_to_wordpress(title, html_body):
    data = {
        'title': title,
        'status': 'draft',
        'content': html_body
    }
    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts",
        json=data,
        auth=(WP_USER, WP_APP_PASS)
    )
    response.raise_for_status()
    return response.json()["link"]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        uploaded_file = request.files['htmlfile']
        rewrite_links = request.form.get("rewrite_links") == "on"
        external_link = request.form.get("external_link", "").strip()
        strip_params = request.form.get("strip_url_params") == "on"

        if uploaded_file.filename.endswith('.html'):
            html_content = uploaded_file.read().decode('utf-8')

            # ✅ 優先：外部リンクにすべて置き換え（指定URL）
            if rewrite_links and external_link:
                html_content = rewrite_all_links(html_content, external_link)
            # ✅ 次点：?以降の削除（リンクのみ、画像は無視）
            elif strip_params:
                html_content = strip_url_parameters_from_links_only(html_content)

            # ✅ 画像差し替え
            new_html = process_html_and_replace_images(html_content)

            # ✅ 投稿
            post_url = post_to_wordpress("アップロード記事", new_html)
            return f"<h2>投稿成功！</h2><a href='{post_url}' target='_blank'>{post_url}</a>"
        else:
            return "HTMLファイル（.html）を選択してください。"
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
