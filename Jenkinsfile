pipeline {
    agent any

    environment {
        S3_BUCKET = 'devops-pipeline-deployments-archana'
        APP_IP    = '172.17.0.1'
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
                    CURRENT=$(docker inspect devops-app --format="{{.Config.Image}}" 2>/dev/null | cut -d: -f2 | tr -d "[:space:]" || echo "none")
                    if [ -z "$CURRENT" ]; then CURRENT="none"; fi
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
                    docker build --no-cache -t devops-app:$VERSION app/
                    echo "Built: $VERSION"
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
                    echo "Waiting 20 seconds..."
                    sleep 30
                    for i in 1 2 3 4 5; do
                        if curl -sf http://$APP_IP:5000/health; then
                            echo "Health check passed!"
                            exit 0
                        fi
                        echo "Attempt $i failed, retrying..."
                        sleep 10
                    done
                    echo "Health check failed"
                    exit 1
                '''
            }
        }

    }

    post {
        success {
            sh '''
                VERSION=v${BUILD_NUMBER}
                curl -s -X POST http://$APP_IP:5000/record-deploy \
                  -H "Content-Type: application/json" \
                  -d "{\"version\":\"$VERSION\",\"status\":\"Success\",\"message\":\"Deployed via Jenkins and Ansible\"}" || true
            '''
            withCredentials([string(credentialsId: 'SLACK_WEBHOOK_URL', variable: 'SLACK_URL')]) {
                sh '''
                    VERSION=v${BUILD_NUMBER}
                    TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M UTC')
                    curl -s -X POST -H 'Content-Type: application/json' \
                    -d "{
                        \\"blocks\\": [
                            {
                                \\"type\\": \\"header\\",
                                \\"text\\": {\\"type\\": \\"plain_text\\", \\"text\\": \\"✅ Deployment success\\"}
                            },
                            {
                                \\"type\\": \\"section\\",
                                \\"fields\\": [
                                    {\\"type\\": \\"mrkdwn\\", \\"text\\": \\"*Version:*\\\\n${VERSION}\\"},
                                    {\\"type\\": \\"mrkdwn\\", \\"text\\": \\"*Time:*\\\\n${TIMESTAMP}\\"}
                                ]
                            },
                            {
                                \\"type\\": \\"section\\",
                                \\"text\\": {\\"type\\": \\"mrkdwn\\", \\"text\\": \\"*Details:*\\\\nDeployment successful. App live at http://100.55.16.227:5000\\"} 
                            },
                            {
                                \\"type\\": \\"actions\\",
                                \\"elements\\": [{\\"type\\": \\"button\\", \\"text\\": {\\"type\\": \\"plain_text\\", \\"text\\": \\"View Pipeline\\"}, \\"url\\": \\"${BUILD_URL}\\"}]
                            }
                        ]
                    }" \
                    "$SLACK_URL"
                '''
            }
        }
        failure {
            sh '''
                PREVIOUS=$(cat /tmp/previous_version.txt 2>/dev/null | tr -d "[:space:]" || echo "none")
                VERSION=v${BUILD_NUMBER}

                if [ "$PREVIOUS" != "none" ] && [ -n "$PREVIOUS" ]; then
                    echo "Rolling back to $PREVIOUS"
                    ansible-playbook ansible/rollback.yml \
                      -e "previous_version=$PREVIOUS s3_bucket=$S3_BUCKET"

                    sleep 15
                    curl -s -X POST http://$APP_IP:5000/record-deploy \
                      -H "Content-Type: application/json" \
                      -d "{\"version\":\"$VERSION\",\"status\":\"Rolled Back\",\"message\":\"Health check failed. Rolled back to $PREVIOUS automatically\"}" || true
                else
                    echo "No previous version to rollback to"
                fi
            '''
            withCredentials([string(credentialsId: 'SLACK_WEBHOOK_URL', variable: 'SLACK_URL')]) {
        sh '''
            VERSION=v${BUILD_NUMBER}
            TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M UTC')
            PREVIOUS=$(cat /tmp/previous_version.txt 2>/dev/null | tr -d "[:space:]" || echo "none")

            if [ "$PREVIOUS" != "none" ] && [ -n "$PREVIOUS" ]; then
                MESSAGE="Deployment failed. Rolled back to $PREVIOUS automatically."
                ICON="⚠️"
            else
                MESSAGE="Deployment failed. No previous version available."
                ICON="❌"
            fi

            curl -s -X POST -H 'Content-Type: application/json' \
            -d "{
                \\"blocks\\": [
                    {
                        \\"type\\": \\"header\\",
                        \\"text\\": {
                            \\"type\\": \\"plain_text\\",
                            \\"text\\": \\"${ICON} Deployment ${VERSION} failed\\"
                        }
                    },
                    {
                        \\"type\\": \\"section\\",
                        \\"fields\\": [
                            {
                                \\"type\\": \\"mrkdwn\\",
                                \\"text\\": \\"*Version:*\\\\n${VERSION}\\"
                            },
                            {
                                \\"type\\": \\"mrkdwn\\",
                                \\"text\\": \\"*Time:*\\\\n${TIMESTAMP}\\"
                            }
                        ]
                    },
                    {
                        \\"type\\": \\"section\\",
                        \\"text\\": {
                            \\"type\\": \\"mrkdwn\\",
                            \\"text\\": \\"*Details:*\\\\n${MESSAGE}\\"
                        }
                    },
                    {
                        \\"type\\": \\"actions\\",
                        \\"elements\\": [
                            {
                                \\"type\\": \\"button\\",
                                \\"text\\": {
                                    \\"type\\": \\"plain_text\\",
                                    \\"text\\": \\"View Pipeline\\"
                                },
                                \\"url\\": \\"${BUILD_URL}\\"
                            }
                        ]
                    }
                ]
            }" \
            "$SLACK_URL"
        '''
    }
}
    }
}

