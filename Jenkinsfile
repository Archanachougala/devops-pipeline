stage('Health Check') {
            steps {
                sh '''
                    echo "Waiting 20 seconds for app to start..."
                    sleep 20

                    for i in 1 2 3 4 5; do
                        if curl -sf http://172.17.0.1:5000/health; then
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
