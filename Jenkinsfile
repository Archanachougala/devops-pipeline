pipeline {
    agent any

    environment {
        S3_BUCKET = 'devops-pipeline-deployments-archana'
        SLACK_CHANNEL = '#deployments'
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
                    echo "Checking health on host port 5000..."
                    curl -f http://localhost:5000/health
                    echo "Health check passed!"
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
                    echo "Deployment v${BUILD_NUMBER} successful!"
                }
            }
        }
    }
}
