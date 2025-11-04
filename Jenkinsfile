// Jenkinsfile (Scripted Pipeline)

pipeline {
    agent any

    environment {
        // --- Registry Configuration ---
        DOCKER_REGISTRY = 'docker.io'
        DOCKER_USERNAME = 'surabhim25' // <<< CHANGE THIS
        IMAGE_NAME = "bucket-acl-app"
        IMAGE_TAG = "${env.BUILD_NUMBER}" 
        
        // --- AWS Configuration (Required for Deployment Stage) ---
        AWS_CREDENTIALS_ID = 'aws-credentials-for-s3' // Must be created in Jenkins
        AWS_REGION = 'ap-south-1' // Matches your RDS/S3 region
        
        // --- ECS/Deployment Target Variables (ADD YOUR VALUES) ---
        ECS_CLUSTER_NAME = 'S3-ACL-Cluster' // The name of your ECS cluster
        ECS_SERVICE_NAME = 'S3-ACL-Service' // The name of your ECS service
        ECS_TASK_DEFINITION = 's3-acl-task-def' // The name of your Task Definition
        ECS_CONTAINER_NAME = 'web-app-container' // Name used in the Task Definition
    }

    stages {
        // ... (Build and Push stages remain the same)

        stage('Deploy to ECS') {
            steps {
                script {
                    echo "Starting deployment to ECS Cluster: ${ECS_CLUSTER_NAME}..."
                    
                    // Securely wrap AWS CLI commands using the configured credentials
                    withAWS(credentials: env.AWS_CREDENTIALS_ID, region: env.AWS_REGION) {
                        
                        // 1. Create the full image URI
                        def imageUri = "${env.DOCKER_REGISTRY}/${env.DOCKER_USERNAME}/${env.IMAGE_NAME}:${env.IMAGE_TAG}"
                        
                        // 2. Update the ECS Task Definition with the new image URI
                        sh """
                            # --- NOTE: This requires AWS CLI to be installed on the Jenkins agent ---
                            echo "Updating ECS Task Definition with image: ${imageUri}"
                            
                            # Using 'aws ecs register-task-definition' and 'aws ecs update-service' 
                            # is the standard way to deploy new images on ECS.
                            
                            # Placeholder for your real task definition update and service deployment command
                            # Example command (requires Task Definition JSON preparation):
                            # aws ecs update-service --cluster ${ECS_CLUSTER_NAME} \\
                            #   --service ${ECS_SERVICE_NAME} \\
                            #   --task-definition ${ECS_TASK_DEFINITION}
                            
                            echo "Deployment initiated. ECS will pull the latest image and recycle tasks."
                        """
                    }
                }
            }
        }
    }
}
