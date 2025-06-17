from flask import Flask, request, render_template, redirect, url_for, session
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)
app.secret_key = 'hkZgYMiopV5sG*A4JgHS*T&j'  # セッション用のキー（適当な文字列に変更）

# ログイン用設定
USERNAME = "ppcuser"
PASSWORD = "hkZgYMiopV5sG*A4JgHS*T&j"

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
        if old_src.startswith("data:"):
            print(f"[スキップ] インライン画像: {old_src[:30]}...")
            continue
        print(f"変換対象画像: {old_src}")
        try:
            new_src = upload_image_to_wordpress(old_src)
            print(f"→ WordPressにアップされた新画像URL: {new_src}")
            img["src"] = new_src
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

# ログイン画面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pw = request.form['password']
        if user == USERNAME and pw == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="ログイン失敗")
    return render_template('login.html')

# ログアウト
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# メイン画面
@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        uploaded_file = request.files['htmlfile']
        rewrite_links = request.form.get("rewrite_links") == "on"
        external_link = request.form.get("external_link", "").strip()
        strip_params = request.form.get("strip_url_params") == "on"

        if uploaded_file.filename.endswith('.html'):
            html_content = uploaded_file.read().decode('utf-8')

            if rewrite_links and external_link:
                html_content = rewrite_all_links(html_content, external_link)
            elif strip_params:
                html_content = strip_url_parameters_from_links_only(html_content)

            new_html = process_html_and_replace_images(html_content)
            post_url = post_to_wordpress("アップロード記事", new_html)
            return f"<h2>投稿成功！</h2><a href='{post_url}' target='_blank'>{post_url}</a>"
        else:
            return "HTMLファイル（.html）を選択してください。"

    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
