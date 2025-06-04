import subprocess
from app.settings import (
    AWS_PROFILE,
    AWS_ACCOUNT_ID,
    AWS_REGION,
    IMAGE_NAME,
    ECR_REPOSITORY_NAME
)

DOCKER_CONTEXT = "desktop-linux"
IMAGE_TAG = "latest"


def build_docker():
    # Define the container name as the image name (modify if different)
    container_name = IMAGE_NAME
    
    # Commands to stop, remove, and build the Docker image
    collectstatic_command = "python manage.py collectstatic --clear --noinput"
    stop_command = f"docker --context {DOCKER_CONTEXT} stop {container_name} || true"
    rm_command = f"docker --context {DOCKER_CONTEXT} rm {container_name} || true"
    build_command = (
        f"docker --context {DOCKER_CONTEXT} buildx build --rm --force-rm --platform=linux/amd64 "
        f"-t {IMAGE_NAME}:{IMAGE_TAG} ."
    )
    
    try:
        subprocess.run(collectstatic_command, shell=True, check=True, timeout=30)
        subprocess.run(stop_command, shell=True, check=False, timeout=30)
        subprocess.run(rm_command, shell=True, check=False, timeout=30)
        subprocess.run(build_command, shell=True, check=True, timeout=30)
    except subprocess.TimeoutExpired as error:
        print(f"Command timed out: {error}")
        print("Try to open Docker Desktop, then reset/resume. Make sure it says Engine running")
    except subprocess.CalledProcessError as error:
        print(f"An error occurred during the Docker build process: {error}")
        print("Try to open Docker Desktop, then reset/resume. Make sure it says Engine running")


def deploy_to_ecr():
    # Construct the AWS ECR registry URL
    ecr_url = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com"

    # Command to login to ECR
    login_command = (
        f"aws ecr get-login-password --region {AWS_REGION} --profile {AWS_PROFILE} | "
        f"docker login --username AWS --password-stdin {ecr_url}"
    )
    
    # Command to tag the Docker image
    tag_command = (
        f"docker --context {DOCKER_CONTEXT} tag {IMAGE_NAME}:{IMAGE_TAG} "
        f"{ecr_url}/{ECR_REPOSITORY_NAME}:{IMAGE_TAG}"
    )
    
    # Command to delete the old image in ECR (if exists)
    delete_command = (
        f"aws ecr batch-delete-image --region {AWS_REGION} --profile {AWS_PROFILE} "
        f"--repository-name {ECR_REPOSITORY_NAME} --image-ids imageTag={IMAGE_TAG}"
    )
    
    # Command to push the Docker image to ECR
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