#include <stdio.h>
int main()
{ float t[31][31];
int i,j ,k;
FILE *fin,*fout;
fin = fopen("C:\\Users\\anuna\\Downloads\\Mintemp_MinT_2025.grd","rb"); 
fout = fopen("C:\\Users\\anuna\\Downloads\\Mintemp_MinT_2025.csv","w"); 
if(fin == NULL)
{ printf("Can't open file");
return 0;
}
if(fout == NULL)
{ printf("Can't open file");
return 0;
}
for(k=0 ; k<366 ; k++)
{ fread(&t,sizeof(t),1,fin) ;
for(i=0 ; i < 31 ; i++)
{ fprintf(fout,"\n") ;
for(j=0 ; j < 31 ; j++)
fprintf(fout,"%6.2f",t[i][j]);
}
}
fclose(fin);
fclose(fout);
return 0;
} 