import subprocess
from grit.core.core_settings import core_settings
AWS_PROFILE = core_settings.AWS_PROFILE
AWS_ACCOUNT_ID = core_settings.AWS_ACCOUNT_ID
AWS_REGION = core_settings.AWS_REGION
IMAGE_NAME = core_settings.IMAGE_NAME
ECR_REPOSITORY_NAME = core_settings.ECR_REPOSITORY_NAME
DOCKER_CONTEXT = "desktop-linux"
IMAGE_TAG = "latest"


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
    ecr_url = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com"
    login_command = (
        f"aws ecr get-login-password --region {AWS_REGION} --profile {AWS_PROFILE} | "
        f"docker login --username AWS --password-stdin {ecr_url}"
    )
    tag_command = (
        f"docker --context {DOCKER_CONTEXT} tag {IMAGE_NAME}:{IMAGE_TAG} "
        f"{ecr_url}/{ECR_REPOSITORY_NAME}:{IMAGE_TAG}"
    )
    delete_command = (
        f"aws ecr batch-delete-image --region {AWS_REGION} --profile {AWS_PROFILE} "
        f"--repository-name {ECR_REPOSITORY_NAME} --image-ids imageTag={IMAGE_TAG}"
    )
    push_command = (
        f"docker --context {DOCKER_CONTEXT} push {ecr_url}/{ECR_REPOSITORY_NAME}:{IMAGE_TAG}"
    )
    try:
        subprocess.run(login_command, shell=True, check=True)
        subprocess.run(tag_command, shell=True, check=True)
        subprocess.run(delete_command, shell=True, check=True)
        subprocess.run(push_command, shell=True, check=True)
    except subprocess.CalledProcessError as error:
        print(f"An error occurred during deployment: {error}")