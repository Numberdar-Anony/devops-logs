import jenkins.model.*
import hudson.security.*
import hudson.model.*
import hudson.tasks.*
import jenkins.security.csrf.*

def instance = Jenkins.getInstance()

// Create admin user
def realm = new HudsonPrivateSecurityRealm(false)
realm.createAccount("admin", "admin123")
instance.setSecurityRealm(realm)

def strategy = new FullControlOnceLoggedInAuthorizationStrategy()
instance.setAuthorizationStrategy(strategy)

// Disable CSRF protection
instance.setCrumbIssuer(null)

instance.save()

// Create failing-build job
def jobName = "failing-build"
if (instance.getItem(jobName) == null) {
    def job = instance.createProject(FreeStyleProject, jobName)
    job.getBuildersList().add(new Shell("echo 'Finished: FAILURE' && echo 'java.lang.NullPointerException' && exit 1"))
    job.save()
    // Trigger first build
    job.scheduleBuild2(0)
}

println "Jenkins setup complete: admin user created and failing-build job configured."
