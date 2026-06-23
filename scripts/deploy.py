import json
import os
import subprocess
from grit.core.core_settings import core_settings
DOCKER_CONTEXT = os.environ.get("DOCKER_CONTEXT", "desktop-linux")
IMAGE_TAG = "latest"
IMAGE_NAME = core_settings.IMAGE_NAME
ECR_REPOSITORY_NAME = core_settings.ECR_REPOSITORY_NAME
REQUIRED_SECRET_KEYS = ["SECRET_KEY"]
AWS_PROFILE = os.environ["AWS_PROFILE"] if "AWS_PROFILE" in os.environ else core_settings.AWS_PROFILE
AWS_PROFILE_FLAG = f"--profile {AWS_PROFILE}" if AWS_PROFILE else ""
if not AWS_PROFILE:
    os.environ.pop("AWS_PROFILE", None)
AWS_ACCOUNT_ID = core_settings.AWS_ACCOUNT_ID
AWS_REGION = core_settings.AWS_REGION
AWS_ECS_CLUSTER = core_settings.AWS_ECS_CLUSTER
AWS_ECS_SERVICE = core_settings.AWS_ECS_SERVICE
AZURE_ACR_REGISTRY_NAME = core_settings.AZURE_ACR_REGISTRY_NAME
AZURE_ACR_REPOSITORY_NAME = core_settings.AZURE_ACR_REPOSITORY_NAME


def detect_provider():
    has_aws = bool(AWS_ACCOUNT_ID)
    has_azure = bool(AZURE_ACR_REGISTRY_NAME)
    if has_aws and has_azure:
        raise RuntimeError(
            "Multiple cloud providers configured. "
            "Set only one of AWS_ACCOUNT_ID or AZURE_ACR_REGISTRY_NAME."
        )
    if not has_aws and not has_azure:
        raise RuntimeError(
            "No cloud provider configured. "
            "Set AWS_ACCOUNT_ID or AZURE_ACR_REGISTRY_NAME in core_settings."
        )
    return "aws" if has_aws else "azure"


def get_git_commit():
    try:
        result = subprocess.run(
            "git rev-parse --short HEAD",
            shell=True, check=True, capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() or "unknown"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unknown"


def build_image(provider):
    print(f"Detected provider: {provider}")
    container_name = IMAGE_NAME
    npm_install_command = "cd frontend && npm install"
    npm_build_command = "cd frontend && npm run build"
    collectstatic_command = "python manage.py collectstatic --clear --noinput"
    stop_command = f"docker --context {DOCKER_CONTEXT} stop {container_name} || true"
    rm_command = f"docker --context {DOCKER_CONTEXT} rm {container_name} || true"
    git_commit = get_git_commit()
    build_command = (
        f"docker --context {DOCKER_CONTEXT} buildx build --rm --force-rm --platform=linux/amd64 "
        f"--build-arg GIT_COMMIT={git_commit} "
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
        print(f"Building Docker image (commit {git_commit})...")
        subprocess.run(stop_command, shell=True, check=False, timeout=30)
        subprocess.run(rm_command, shell=True, check=False, timeout=30)
        subprocess.run(build_command, shell=True, check=True, timeout=600)
        print("Docker image built successfully.")
    except subprocess.TimeoutExpired as error:
        print(f"Command timed out: {error}")
        print("Try to open Docker Desktop, then reset/resume. Make sure it says Engine running")
        raise
    except subprocess.CalledProcessError as error:
        print(f"An error occurred during the build process: {error}")
        if "npm" in str(error.cmd):
            print("Make sure Node.js and npm are installed on your system.")
        else:
            print("Try to open Docker Desktop, then reset/resume. Make sure it says Engine running")
        raise


def deploy(provider):
    if provider == "aws":
        _deploy_aws()
    else:
        _deploy_azure()


def _discover_ecs_service(ecs_cluster, name_substring):
    list_command = (
        f"aws ecs list-services --region {AWS_REGION} {AWS_PROFILE_FLAG} "
        f"--cluster {ecs_cluster} --output json"
    )
    try:
        result = subprocess.run(
            list_command, shell=True, check=True, capture_output=True, text=True, timeout=30,
        )
        service_arns = json.loads(result.stdout).get("serviceArns", [])
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"Could not list ECS services for discovery: {error}")
        return None
    matches = [
        arn.rsplit("/", 1)[-1]
        for arn in service_arns
        if name_substring in arn.rsplit("/", 1)[-1]
    ]
    if len(matches) == 1:
        print(f"Discovered ECS service '{matches[0]}' on cluster '{ecs_cluster}'.")
        return matches[0]
    if len(matches) > 1:
        print(
            f"Multiple ECS services match '{name_substring}' on cluster '{ecs_cluster}': "
            f"{matches}. Set AWS_ECS_SERVICE explicitly to disambiguate."
        )
    else:
        print(
            f"No ECS service matching '{name_substring}' found on cluster '{ecs_cluster}'."
        )
    return None


def _assert_secret_has_keys(secret_id):
    if not secret_id:
        print("WARNING: AWS_SECRETS_MANAGER_SECRET_ID is not set; the Secrets Manager "
              "tier is disabled and the app will rely on environment variables. "
              "Skipping the secret preflight.")
        return
    get_secret_command = (
        f"aws secretsmanager get-secret-value --region {AWS_REGION} {AWS_PROFILE_FLAG} "
        f"--secret-id {secret_id} --query 'SecretString' --output text"
    )
    try:
        result = subprocess.run(
            get_secret_command, shell=True, capture_output=True, text=True, timeout=30,
        )
    except subprocess.TimeoutExpired as error:
        print(f"WARNING: timed out reading secret '{secret_id}' ({error}); "
              f"skipping the preflight.")
        return
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        if "ResourceNotFoundException" in stderr:
            raise RuntimeError(
                f"Secrets Manager secret '{secret_id}' does not exist. New tasks would "
                f"crash-loop on boot ('required credential(s) not set: SECRET_KEY'). "
                f"Create it with `./internal/sync_secret.sh` (from a machine with "
                f"credentials.json), then re-run the deploy."
            )
        print(f"WARNING: could not read secret '{secret_id}' to verify it "
              f"({stderr or 'unknown error'}); skipping the preflight.")
        return
    try:
        secret = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"WARNING: secret '{secret_id}' is not valid JSON; skipping the preflight.")
        return
    missing = [key for key in REQUIRED_SECRET_KEYS if not secret.get(key)]
    if missing:
        raise RuntimeError(
            f"Secrets Manager secret '{secret_id}' is missing required key(s): "
            f"{', '.join(missing)}. New tasks would boot but crash/500 on every request. "
            f"Add them with `./internal/sync_secret.sh` (from a machine with "
            f"credentials.json), then re-run the deploy."
        )
    print(f"Preflight OK: secret '{secret_id}' has required key(s) "
          f"{', '.join(REQUIRED_SECRET_KEYS)}.")


def _deploy_aws():
    ecr_url = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com"
    login_command = (
        f"aws ecr get-login-password --region {AWS_REGION} {AWS_PROFILE_FLAG} | "
        f"docker login --username AWS --password-stdin {ecr_url}"
    )
    tag_command = (
        f"docker --context {DOCKER_CONTEXT} tag {IMAGE_NAME}:{IMAGE_TAG} "
        f"{ecr_url}/{ECR_REPOSITORY_NAME}:{IMAGE_TAG}"
    )
    delete_command = (
        f"aws ecr batch-delete-image --region {AWS_REGION} {AWS_PROFILE_FLAG} "
        f"--repository-name {ECR_REPOSITORY_NAME} --image-ids imageTag={IMAGE_TAG}"
    )
    push_command = (
        f"docker --context {DOCKER_CONTEXT} push {ecr_url}/{ECR_REPOSITORY_NAME}:{IMAGE_TAG}"
    )
    ecs_cluster = AWS_ECS_CLUSTER or "default"
    ecs_service = (
        AWS_ECS_SERVICE
        or _discover_ecs_service(ecs_cluster, ECR_REPOSITORY_NAME)
        or ECR_REPOSITORY_NAME
    )
    update_service_command = (
        f"aws ecs update-service --region {AWS_REGION} {AWS_PROFILE_FLAG} "
        f"--cluster {ecs_cluster} --service {ecs_service} --force-new-deployment "
        f"--query 'service.serviceName' --output text"
    )
    try:
        _assert_secret_has_keys(core_settings.AWS_SECRETS_MANAGER_SECRET_ID)
        subprocess.run(login_command, shell=True, check=True)
        subprocess.run(tag_command, shell=True, check=True)
        subprocess.run(delete_command, shell=True, check=True)
        subprocess.run(push_command, shell=True, check=True)
        print(f"Triggering ECS deployment for service '{ecs_service}' on cluster '{ecs_cluster}'...")
        subprocess.run(update_service_command, shell=True, check=True)
        print("ECS service update requested. New tasks will pull the latest image.")
    except subprocess.CalledProcessError as error:
        print(f"An error occurred during deployment: {error}")
        raise


def _deploy_azure():
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
        raise
