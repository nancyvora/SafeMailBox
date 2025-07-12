rule dummy_malware
{
    strings:
        $mz = "MZ"
    condition:
        $mz at 0
}
