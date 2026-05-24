pipeline {
    agent any

    environment {
        S3_BUCKET = 'devops-pipeline-deployments-archana'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Save Previous Version') {
            steps {
                sh '''
                    CURRENT=$(docker inspect devops-app --format="{{.Config.Image}}" 2>/dev/null | cut -d: -f2 | tr -d '[:space:]' || echo "none")
                    if [ -z "$CURRENT" ]; then
                        CURRENT="none"
                    fi
                    echo "Previous version: $CURRENT"
                    echo $CURRENT > /tmp/previous_version.txt
                    aws s3 cp /tmp/previous_version.txt s3://$S3_BUCKET/previous_version.txt || true
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    VERSION=v${BUILD_NUMBER}
                    docker build -t devops-app:$VERSION .
                    echo "Built version: $VERSION"
                '''
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    VERSION=v${BUILD_NUMBER}
                    ansible-playbook ansible/deploy.yml -e "version=$VERSION"
                '''
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                    echo "Waiting 20 seconds for app to start..."
                    sleep 20

                    HOST_IP=$(ip route | grep default | awk '{print $3}')
                    echo "Host IP: $HOST_IP"

                    for i in 1 2 3 4 5; do
                        if curl -sf http://$HOST_IP:5000/health; then
                            echo "Health check passed!"
                            exit 0
                        fi
                        echo "Attempt $i failed, retrying in 10 seconds..."
                        sleep 10
                    done

                    echo "All health check attempts failed"
                    exit 1
                '''
            }
            post {
                failure {
                    sh '''
                        echo "Health check failed. Triggering rollback..."
                        ansible-playbook ansible/rollback.yml
                    '''
                }
                success {
                    echo "Deployment successful!"
                }
            }
        }
    }
}
