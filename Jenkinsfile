pipeline {
    agent any

    environment {
        S3_BUCKET = 'devops-pipeline-deployments-archana'
        APP_IP = 'localhost'
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
                    CURRENT=$(docker inspect devops-app --format={{.Config.Image}} 2>/dev/null || echo "none")
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
                    echo "Waiting 15 seconds for app to start..."
                    sleep 15
                    curl -f http://$APP_IP:5000/health
                '''
            }
            post {
                failure {
                    sh 'ansible-playbook ansible/rollback.yml'
                    slackSend(
                        channel: env.SLACK_CHANNEL,
                        color: 'danger',
                        message: "❌ Deployment v${BUILD_NUMBER} FAILED — automatically rolled back!"
                    )
                }
                success {
                    slackSend(
                        channel: env.SLACK_CHANNEL,
                        color: 'good',
                        message: "✅ Deployment v${BUILD_NUMBER} successful and healthy!"
                    )
                }
            }
        }
    }
}
