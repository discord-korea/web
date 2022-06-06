import os

import aiohttp
import jwt
from quart import (
    Quart,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from requests_oauthlib import OAuth2Session

import config

app = Quart(__name__)

app.config["SECRET_KEY"] = config.app.client_secret

AUTHORIZATION_BASE_URL = "https://discord.com/api/oauth2/authorize"
TOKEN_URL = "https://discord.com/api/oauth2/token"

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

if "http://" in config.app.client_secret:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"


def make_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=config.app.client_id,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=config.app.redirect_uri,
        auto_refresh_kwargs={
            "client_id": config.app.client_id,
            "client_secret": app.config["SECRET_KEY"],
        },
        auto_refresh_url=TOKEN_URL,
        token_updater=token_updater,
    )


def token_updater(token):
    session["discord_oauth2_token"] = token


async def getUser():
    try:
        discordoauth = make_session(
            jwt.decode(
                session["discord_oauth2_token"],
                config.app.client_secret,
                algorithms=["HS256"],
            )
        )

        user = discordoauth.get("https://discord.com/api/users/@me").json()
        name = f"{user['username']}#{user['discriminator']}"
        if user["avatar"] == None:
            if (
                str(user["discriminator"])[3] == "0"
                or str(user["discriminator"])[3] == "5"
            ):
                avatar_url = f"https://cdn.discordapp.com/embed/avatars/0.png"
            elif (
                str(user["discriminator"])[3] == "1"
                or str(user["discriminator"])[3] == "6"
            ):
                avatar_url = f"https://cdn.discordapp.com/embed/avatars/1.png"
            elif (
                str(user["discriminator"])[3] == "2"
                or str(user["discriminator"])[3] == "7"
            ):
                avatar_url = f"https://cdn.discordapp.com/embed/avatars/2.png"
            elif (
                str(user["discriminator"])[3] == "3"
                or str(user["discriminator"])[3] == "8"
            ):
                avatar_url = f"https://cdn.discordapp.com/embed/avatars/3.png"
            elif (
                str(user["discriminator"])[3] == "4"
                or str(user["discriminator"])[3] == "9"
            ):
                avatar_url = f"https://cdn.discordapp.com/embed/avatars/4.png"
        else:
            avatar_url = (
                f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png"
            )
        return {
            "id": user["id"],
            "name": name,
            "avatar_url": avatar_url,
            "discord_userinfo": user,
        }
    except:
        return None


@app.before_request
async def before_request():
    if any(
        page in request.path for page in ["/login", "/static", "/auth", "/favicon.ico"]
    ):
        return
    session["last_page"] = request.path


@app.errorhandler(404)
async def error_404(error):
    return await render_template("404.html", user=await getUser(), title="404"), 404


@app.route("/favicon.ico")
async def favicon():
    return await send_from_directory(
        os.path.join(app.root_path, "static"),
        "images/favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/")
async def index():
    return await render_template("index.html", user=await getUser(), title="메인")


@app.route("/discord")
async def discord():
    return await render_template("redirect.html", redirect_url="https://discord.gg/TD9BvMxhP6", user=await getUser(), title="디스코드 이동하기")


@app.route("/service")
async def service_list():
    return await render_template("redirect.html", redirect_url="https://discord.gg/TD9BvMxhP6", user=await getUser(), title="디스코드 이동하기")


@app.route("/service/<string:service_id>")
async def service_show(service_id: str):
    if service_id == "":
        return await redirect("/service")
    elif service_id == "happytreebot":
        return await render_template("redirect.html", redirect_url="https://htb.htlab.kr", user=await getUser(), title="서비스: 해피트리봇")
    elif service_id == "herbbot":
        return abort(404)
    else:
        return abort(404)


@app.route("/login")
async def login():
    discordoauth = make_session(scope=["identify"])
    authorization_url, state = discordoauth.authorization_url(AUTHORIZATION_BASE_URL)
    session["discord_oauth2_state"] = state
    return await render_template(
        "login.html", title="로그인", oauth2_link=authorization_url
    )


@app.route("/auth/discord")
async def auth_discord():
    try:
        if request.args.get("error"):
            return f"{request.args.get('error')}"

        if request.args.get("state") != session["discord_oauth2_state"]:
            return "Invalid state"

        discordoauth = make_session()
        token = discordoauth.fetch_token(
            TOKEN_URL,
            client_secret=config.app.client_secret,
            authorization_response=request.url,
        )
        user = discordoauth.get("https://discord.com/api/users/@me").json()
    except:
        return redirect("/login")
    session["discord_oauth2_token"] = jwt.encode(
        token, config.app.client_secret, algorithm="HS256"
    )
    del session["discord_oauth2_state"]
    return redirect(session["last_page"] if session["last_page"] else "/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
