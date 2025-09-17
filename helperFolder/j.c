#include <linux/module.h>      // Needed by all modules
#include <linux/kernel.h>      // Needed for KERN_INFO
#include <linux/proc_fs.h>     // Needed for proc fs
#include <linux/jiffies.h>     // Needed for jiffies
#include <linux/uaccess.h>     // Needed for copy_to_user

#define PROC_NAME "jiffies"

ssize_t proc_read(struct file *file, char __user *buf, size_t count, loff_t *pos)
{
    char buffer[64];
    int len;

    // Prepare the string with current jiffies value
    len = snprintf(buffer, sizeof(buffer), "%lu\n", jiffies);

    // Only allow reading once
    if (*pos > 0 || count < len)
        return 0;

    // Copy data to user space
    if (copy_to_user(buf, buffer, len))
        return -EFAULT;

    *pos = len; // update file position
    return len;
}

// Use proc_ops for newer kernels (>= 5.6)
static const struct proc_ops fops = {
    .proc_read = proc_read,
};

// Function called when module is loaded
static int __init jiffies_init(void)
{
    proc_create(PROC_NAME, 0, NULL, &fops);  // create /proc/jiffies
    printk(KERN_INFO "/proc/%s created\n", PROC_NAME);
    return 0;
}

// Function called when module is removed
static void __exit jiffies_exit(void)
{
    remove_proc_entry(PROC_NAME, NULL);      // remove /proc/jiffies
    printk(KERN_INFO "/proc/%s removed\n", PROC_NAME);
}

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Kernel module to show current jiffies");
MODULE_AUTHOR("Dhruv Patel");

module_init(jiffies_init);
module_exit(jiffies_exit);
