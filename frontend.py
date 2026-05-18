import streamlit as st
import requests
import base64
import urllib.parse

from streamlit_cookies_manager import EncryptedCookieManager

st.set_page_config(page_title="Simple Social", layout="wide")
cookies = EncryptedCookieManager(
    prefix="simple_social/",
    password="super-secret-password"
)

if not cookies.ready():
    st.stop()

# Initialize session state
# if 'token' not in st.session_state:
#     st.session_state.token = None
# Restore token from cookie
if 'token' not in st.session_state:
    st.session_state.token = cookies.get("token")
if 'user' not in st.session_state:
    st.session_state.user = None

# Restore user from token
if st.session_state.token and st.session_state.user is None:

    response = requests.get(
        "http://localhost:8000/users/me",
        headers={
            "Authorization": f"Bearer {st.session_state.token}"
        }
    )

    if response.status_code == 200:
        st.session_state.user = response.json()
    else:
        st.session_state.token = None
        cookies["token"] = ""
        cookies.save()


def get_headers():
    """Get authorization headers with token"""
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


def login_page():
    st.title("🚀 Welcome to Simple Social")

    # Simple form with two buttons
    email = st.text_input("Email:")
    password = st.text_input("Password:", type="password")

    if email and password:
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Login", type="primary", use_container_width=True):
                # Login using FastAPI Users JWT endpoint
                login_data = {"username": email, "password": password}
                response = requests.post("http://localhost:8000/auth/jwt/login", data=login_data)

                if response.status_code == 200:
                    token_data = response.json()
                    st.session_state.token = token_data["access_token"]

                    cookies["token"] = token_data["access_token"]
                    cookies.save()

                    # Get user info
                    user_response = requests.get("http://localhost:8000/users/me", headers=get_headers())
                    if user_response.status_code == 200:
                        st.session_state.user = user_response.json()
                        st.rerun()
                    else:
                        st.error("Failed to get user info")
                else:
                    st.error("Invalid email or password!")

        with col2:
            if st.button("Sign Up", type="secondary", use_container_width=True):
                # Register using FastAPI Users
                signup_data = {"email": email, "password": password}
                response = requests.post("http://localhost:8000/auth/register", json=signup_data)

                if response.status_code == 201:
                    st.success("Account created! Click Login now.")
                else:
                    error_detail = response.json().get("detail", "Registration failed")
                    st.error(f"Registration failed: {error_detail}")
    else:
        st.info("Enter your email and password above")


def upload_page():
    st.title("📸 Share Something")

    uploaded_file = st.file_uploader("Choose media", type=['png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov', 'mkv', 'webm'])
    caption = st.text_area("Caption:", placeholder="What's on your mind?")

    if uploaded_file and st.button("Share", type="primary"):
        with st.spinner("Uploading..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {"caption": caption}
            response = requests.post("http://localhost:8000/upload", files=files, data=data, headers=get_headers())

            if response.status_code == 200:
                st.success("Posted!")
                st.rerun()
            else:
                st.error("Upload failed!")


def encode_text_for_overlay(text):
    """Encode text for ImageKit overlay - base64 then URL encode"""
    if not text:
        return ""
    # Base64 encode the text
    base64_text = base64.b64encode(text.encode('utf-8')).decode('utf-8')
    # URL encode the result
    return urllib.parse.quote(base64_text)


def create_transformed_url(original_url, transformation_params, caption=None):
    if caption:
        encoded_caption = encode_text_for_overlay(caption)
        # Add text overlay at bottom with semi-transparent background
        text_overlay = f"l-text,ie-{encoded_caption},ly-N20,lx-20,fs-100,co-white,bg-000000A0,l-end"
        transformation_params = text_overlay

    if not transformation_params:
        return original_url

    parts = original_url.split("/")

    imagekit_id = parts[3]
    file_path = "/".join(parts[4:])
    base_url = "/".join(parts[:4])
    return f"{base_url}/tr:{transformation_params}/{file_path}"


def feed_page():
    st.title("🏠 Feed")

    response = requests.get("http://localhost:8000/feed", headers=get_headers())
    if response.status_code == 200:
        posts = response.json()["posts"]

        if not posts:
            st.info("No posts yet! Be the first to share something.")
            return

        for post in posts:
            st.markdown("---")

            # Header with user, date, and delete button (if owner)
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{post['email']}** • {post['created_at'][:10]}")
            with col2:
                if post.get('is_owner', False):
                    if st.button("🗑️", key=f"delete_{post['id']}", help="Delete post"):
                        # Delete the post
                        response = requests.delete(f"http://localhost:8000/posts/{post['id']}", headers=get_headers())
                        if response.status_code == 200:
                            st.success("Post deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete post!")

            # Uniform media display with caption overlay
            # Main content layout
            media_col, comment_col = st.columns([1.3, 1])

            # MEDIA SECTION
            with media_col:

                caption = post.get('caption', '')

                if post['file_type'] == 'image':

                    uniform_url = create_transformed_url(
                        post['url'],
                        "",
                        caption
                    )

                    st.image(uniform_url, width=320)

                else:

                    uniform_video_url = create_transformed_url(
                        post['url'],
                        "w-400,h-200,cm-pad_resize,bg-blurred"
                    )

                    st.video(uniform_video_url)

                    st.caption(caption)

                # Likes section
                likes_count = post.get("likes", 0)
                is_liked = post.get("is_liked", False)

                heart_icon = "❤️" if is_liked else "🤍"
                st.write(f"{heart_icon} {likes_count} likes")

                if is_liked:
                    if st.button(
                            "Unlike",
                            key=f"unlike_{post['id']}"
                    ):

                        unlike_response = requests.post(
                            "http://localhost:8000/unlike",
                            params={"post_id": post["id"]},
                            headers=get_headers()
                        )

                        if unlike_response.status_code == 200:

                            st.success("Unliked!")
                            st.rerun()

                        else:

                            st.error(
                                unlike_response.json().get(
                                    "detail",
                                    "Failed to unlike"
                                )
                            )

                else:

                    if st.button(
                            "Like",
                            key=f"like_{post['id']}"
                    ):

                        like_response = requests.post(
                            "http://localhost:8000/like",
                            params={"post_id": post["id"]},
                            headers=get_headers()
                        )

                        if like_response.status_code == 200:

                            st.success("Liked!")
                            st.rerun()

                        else:

                            st.error(
                                like_response.json().get(
                                    "detail",
                                    "Failed to like"
                                )
                            )

            # COMMENT SECTION
            with comment_col:

                st.markdown("### 💬 Comments")

                comments = post.get("comments", [])

                if comments:

                    for comment in comments:
                        st.write(
                            f"🗨️ {comment['text']}"
                        )

                else:

                    st.caption("No comments yet")

                st.markdown("---")

                comment_text = st.text_input(
                    "Add comment",
                    key=f"comment_input_{post['id']}"
                )

                if st.button(
                        "Post Comment",
                        key=f"comment_btn_{post['id']}"
                ):

                    if comment_text.strip():

                        comment_response = requests.post(
                            "http://localhost:8000/comments",
                            params={
                                "text": comment_text,
                                "post_id": post["id"]
                            },
                            headers=get_headers()
                        )

                        if comment_response.status_code == 200:

                            st.success("Comment added!")
                            st.rerun()

                        else:

                            st.error(
                                comment_response.json().get(
                                    "detail",
                                    "Failed to add comment"
                                )
                            )




            # caption = post.get('caption', '')
            # if post['file_type'] == 'image':
            #     uniform_url = create_transformed_url(post['url'], "", caption)
            #     st.image(uniform_url, width=300)
            # else:
            #     # For videos: specify only height to maintain aspect ratio + caption overlay
            #     uniform_video_url = create_transformed_url(post['url'], "w-400,h-200,cm-pad_resize,bg-blurred")
            #     st.video(uniform_video_url, width=300)
            #     st.caption(caption)
            #
            # st.markdown("")  # Space between posts
            #
            #
            #
            # # Like + Comment Section
            # col1, col2 = st.columns([1, 3])
            #
            # with col1:
            #     likes_count = post.get("likes", 0)
            #
            #     st.write(f"❤️ {likes_count} likes")
            #
            #     if st.button("Like", key=f"like_{post['id']}"):
            #
            #         like_response = requests.post(
            #             "http://localhost:8000/like",
            #             params={"post_id": post["id"]},
            #             headers=get_headers()
            #         )
            #
            #         if like_response.status_code == 200:
            #             st.success("Liked!")
            #             st.rerun()
            #
            #         else:
            #             st.error(
            #                 like_response.json().get(
            #                     "detail",
            #                     "Failed to like"
            #                 )
            #             )
            #
            # with col2:
            #
            #     st.write("💬 Comments")
            #
            #     comments = post.get("comments", [])
            #
            #     if comments:
            #
            #         for comment in comments:
            #             st.write(
            #                 f"🗨️ {comment['text']}"
            #             )
            #
            #     else:
            #         st.caption("No comments yet")
            #
            #     # Add Comment
            #     comment_text = st.text_input(
            #         "Add comment",
            #         key=f"comment_input_{post['id']}"
            #     )
            #
            #     if st.button(
            #             "Post Comment",
            #             key=f"comment_btn_{post['id']}"
            #     ):
            #
            #         if comment_text.strip():
            #
            #             comment_response = requests.post(
            #                 "http://localhost:8000/comments",
            #                 params={
            #                     "text": comment_text,
            #                     "post_id": post["id"]
            #                 },
            #                 headers=get_headers()
            #             )
            #
            #             if comment_response.status_code == 200:
            #
            #                 st.success("Comment added!")
            #                 st.rerun()
            #
            #             else:
            #
            #                 st.error(
            #                     comment_response.json().get(
            #                         "detail",
            #                         "Failed to add comment"
            #                     )
            #                 )
    else:
        st.error("Failed to load feed")


# Main app logic
if st.session_state.user is None:
    login_page()
else:
    # Sidebar navigation
    st.sidebar.title(f"👋 Hi {st.session_state.user['email']}!")

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.token = None

        cookies["token"] = ""
        cookies.save()

        st.rerun()

    st.sidebar.markdown("---")
    page = st.sidebar.radio("Navigate:", ["🏠 Feed", "📸 Upload"])

    if page == "🏠 Feed":
        feed_page()
    else:
        upload_page()