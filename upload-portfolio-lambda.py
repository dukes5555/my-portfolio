import boto3
import StringIO
import zipfile
import mimetypes

def lambda_handler(event, context):

	#Get SNS resource from boto3
    sns = boto3.resource('sns')

    #provide topic ARN to notify admin of successful builds or failed builds
    topic = sns.Topic('arn:aws:sns:us-east-1:414370728305:deployPortfolioTopic')

    #create a default location for portfolio builds that are not triggered by codepipeline
    location = {
        "bucketName": 'portfoliobuild.nickcaccese.com',
        "objectKey": 'portfoliobuild.zip'
    }
    
    #try,except to catch errors
    try:
    	#get codepipeline job event
        job = event.get("CodePipeline.job")
        
        #check to see if codepipeline triggered this lambda function
        if job:
            for artifact in job["data"]["inputArtifacts"]:
                if artifact["name"] == "MyAppBuild":
                	#if an artifact was created by codebuild, get the location of the artifact from the codepipeline event object
                    location = artifact["location"]["s3Location"]
        
        #write to the logs the location in s3 of the build being used
        print "Building portfolio from " + str(location)
        
        #get the s3 resource from boto3
        s3 = boto3.resource('s3')
        
        #set the bucket to deploy the portfolio to
        portfolio_bucket = s3.Bucket('portfolio.nickcaccese.com')
        
        #set the build bucket from the location object
        build_bucket = s3.Bucket(location["bucketName"])
       
       	#create a stringIO object to process the build artifact in memory
        portfolio_zip = StringIO.StringIO()

        #download the build artifact using the stringIO object
        build_bucket.download_fileobj(location["objectKey"], portfolio_zip)
        
        #using the stringIO object, get each file, set them as public, and put them in the s3 portfolio bucket
        with zipfile.ZipFile(portfolio_zip) as myzip:
            for nm in myzip.namelist():
                obj = myzip.open(nm)
                portfolio_bucket.upload_fileobj(obj, nm,
                    ExtraArgs={'ContentType': mimetypes.guess_type(nm)[0]})
                portfolio_bucket.Object(nm).Acl().put(ACL='public-read')
                
        print "Job done!"
        
        #publish to topic that the portfolio deployment was successful
        topic.publish(Subject="Portfolio Deployed", Message="Portfolio deployed successfully!")

        #if the function was invoked from codepipeline, tell codepipeline that it was succesful
        if job:
            codepipeline = boto3.client('codepipeline')
            codepipeline.put_job_success_result(jobId=job["id"])

    #if an error occurs, this is invoked    
    except:
    	#notify the admin that something caused the portfolio deployment to fail
        topic.publish(Subject="Portfolio Deploy Failed", Message="The Portfolio was not deployed succesfully.")
        raise
    
    
    return 'This function ran!'