import os
from datetime import datetime

class Variant:
    def __init__(self, id, gt, file):
        self.id = id
        self._1_0 = 0
        self._0_1 = 0
        self._1__1 = 0
        self._d__d = 0
        self._0__0 = 0
        self._0__1 = 0
        self._1__2 = 0
        match gt:
            case '1|0':
                self._1_0 = 1
            case '0|1':
                self._0_1 = 1
            case '1/1':
                self._1__1 = 1
            case './.':
                self._d__d = 1
            case '0/0':
                self._0__0 = 1
            case '0/1':
                self._0__1 = 1
            case '1/2':
                self._1__2 = 1
        self.total = 1
        self.fileList = [file]
    def updateCount(self, gt, file):
        if file not in self.fileList:
            match gt:
                case '1|0':
                    self._1_0 += 1
                case '0|1':
                    self._0_1 += 1
                case '1/1':
                    self._1__1 += 1
                case './.':
                    self._d__d += 1
                case '0/0':
                    self._0__0 += 1
                case '0/1':
                    self._0__1 += 1
                case '1/2':
                    self._1__2 += 1
            self.total += 1
            if file not in self.fileList:
                self.fileList.append(file)
    def printLine(self):
        filenums = map(str, self.fileList)
        output = f'{self.id},{self._1_0},{self._0_1},{self._1__1},{self._d__d},{self._0__0},{self._0__1},{self._1__2},{self.total},{";".join(filenums)}\n'
        return output


def findMerged(path, filelist=[]):
    for item in os.listdir(path):
        full_path = os.path.join(path, item)
        if os.path.isfile(full_path) and full_path.endswith('_merged.bed'):
            filelist = filelist + [full_path]
            return filelist
    for item in os.listdir(path):
        full_path = os.path.join(path, item)
        if os.path.isdir(full_path):
            filelist = findMerged(full_path, filelist)
    return filelist

# filelist = findMerged('/mnt/synology3/polar_pipeline')
# for item in findMerged('/mnt/synology4/polar_pipeline'):
#     if item.replace('synology3', 'synology4') not in filelist:
#         filelist.append(item)

filelist = []
for path in open('fixedList.txt'):
    if path:
        filelist.append(path.strip())

# print(filelist)
# quit()

current_datetime = datetime.now()
formatted_datetime = current_datetime.strftime("%d-%m-%y_%H-%M-%S")
os.mkdir(formatted_datetime)

variants = {}
filekey = {}
for fileindex, file in enumerate(filelist):
# for fileindex in range(2):
    # file = filelist[fileindex]
    print(os.path.basename(file))
    if file not in filekey:
        filekey[file] = fileindex
    colkey = {}
    for row in open(file):
        line = row.strip().split('\t')
        if row.startswith('#'):
            for index, col in enumerate(line):
                colkey[col] = index
            continue
        id = f'{line[colkey["#CHROM"]]}_{line[colkey["POS"]]}_{line[colkey["REF"]]}/{line[colkey["ALT"]]}'
        if id in variants:
            variants[id].updateCount(line[colkey['GT']], fileindex)
        else:
            variant = Variant(id, line[colkey['GT']], fileindex)
            variants[id] = variant

    with open(f'{formatted_datetime}/variantCatalogue.tsv', 'w') as opened:
        for variant in variants:
            opened.write(variants[variant].printLine())

    with open(f'{formatted_datetime}/fileKey.tsv', 'w') as opened:
        for file in filekey:
            opened.write(f'{file}\t{filekey[file]}\n')