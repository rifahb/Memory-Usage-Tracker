#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/mm.h>

#define PROC_NAME "mem_tracker"

static int mem_show(struct seq_file *m, void *v) {
    struct sysinfo info;
    si_meminfo(&info);

    unsigned long total = info.totalram * 4 / 1024;  // in KB
    unsigned long free = info.freeram * 4 / 1024;
    unsigned long used = total - free;

    seq_printf(m, "Used: %lu\nTotal: %lu\n", used, total);
    return 0;
}

static int mem_open(struct inode *inode, struct file *file) {
    return single_open(file, mem_show, NULL);
}

static const struct proc_ops mem_fops = {
    .proc_open = mem_open,
    .proc_read = seq_read,
    .proc_lseek = seq_lseek,
    .proc_release = single_release,
};

static int __init my_memtracker_init(void) {
    proc_create(PROC_NAME, 0, NULL, &mem_fops);
    printk(KERN_INFO "mem_tracker loaded\n");
    return 0;
}

static void __exit my_memtracker_exit(void) {
    remove_proc_entry(PROC_NAME, NULL);
    printk(KERN_INFO "mem_tracker removed\n");
}

MODULE_LICENSE("GPL");
MODULE_AUTHOR("You");
MODULE_DESCRIPTION("A memory tracker LKM");

module_init(my_memtracker_init);
module_exit(my_memtracker_exit);
