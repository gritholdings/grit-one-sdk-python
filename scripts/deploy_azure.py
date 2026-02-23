import subprocess
from app.settings import CORE_SETTINGS, IMAGE_NAME
DOCKER_CONTEXT = "desktop-linux"
IMAGE_TAG = "latest"
AZURE_ACR_REGISTRY_NAME = CORE_SETTINGS.get('AZURE_ACR_REGISTRY_NAME', '')
AZURE_ACR_REPOSITORY_NAME = CORE_SETTINGS.get('AZURE_ACR_REPOSITORY_NAME', '')


def build_image():
    container_name = IMAGE_NAME
    npm_install_command = "cd frontend && npm install"
    npm_build_command = "cd frontend && npm run build"
    collectstatic_command = "python manage.py collectstatic --clear --noinput"
    stop_command = f"docker --context {DOCKER_CONTEXT} stop {container_name} || true"
    rm_command = f"docker --context {DOCKER_CONTEXT} rm {container_name} || true"
    build_command = (
        f"docker --context {DOCKER_CONTEXT} buildx build --rm --force-rm --platform=linux/amd64 "
        f"-t {IMAGE_NAME}:{IMAGE_TAG} ."
    )
    try:
        print("Installing frontend dependencies...")
        subprocess.run(npm_install_command, shell=True, check=True, timeout=300)
        print("Building frontend assets...")
        subprocess.run(npm_build_command, shell=True, check=True, timeout=120)
        print("Frontend build completed successfully.")
        print("Collecting static files...")
        subprocess.run(collectstatic_command, shell=True, check=True, timeout=30)
        print("Building Docker image...")
        subprocess.run(stop_command, shell=True, check=False, timeout=30)
        subprocess.run(rm_command, shell=True, check=False, timeout=30)
        subprocess.run(build_command, shell=True, check=True, timeout=600)
        print("Docker image built successfully.")
    except subprocess.TimeoutExpired as error:
        print(f"Command timed out: {error}")
        print("Try to open Docker Desktop, then reset/resume. Make sure it says Engine running")
    except subprocess.CalledProcessError as error:
        print(f"An error occurred during the build process: {error}")
        if "npm" in str(error.cmd):
            print("Make sure Node.js and npm are installed on your system.")
        else:
            print("Try to open Docker Desktop, then reset/resume. Make sure it says Engine running")


def deploy():
    acr_url = f"{AZURE_ACR_REGISTRY_NAME}.azurecr.io"
    login_command = f"az acr login --name {AZURE_ACR_REGISTRY_NAME}"
    tag_command = (
        f"docker --context {DOCKER_CONTEXT} tag {IMAGE_NAME}:{IMAGE_TAG} "
        f"{acr_url}/{AZURE_ACR_REPOSITORY_NAME}:{IMAGE_TAG}"
    )
    push_command = (
        f"docker --context {DOCKER_CONTEXT} push {acr_url}/{AZURE_ACR_REPOSITORY_NAME}:{IMAGE_TAG}"
    )
    try:
        subprocess.run(login_command, shell=True, check=True)
        subprocess.run(tag_command, shell=True, check=True)
        subprocess.run(push_command, shell=True, check=True)
    except subprocess.CalledProcessError as error:
        print(f"An error occurred during deployment: {error}")
